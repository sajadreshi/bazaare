"""Reading the catalog: collections, categories, products and the home page.

Only active collections, categories and products are ever shown to shoppers.
"""

from dataclasses import dataclass, field

from app.extension import db
from app.models import Carousel, Category, HomePageContent, Product
from app.services.cart import line_price, product_variants


@dataclass
class HomePage:
    hero_image: str | None = None
    slides: list = field(default_factory=list)
    featured: list = field(default_factory=list)
    featured_title: str | None = None


def active_products(category):
    return category.product.filter(Product.is_active.is_(True)).order_by(Product.id).all()


def get_product(product_id):
    product = db.session.get(Product, product_id)
    return product if product is not None and product.is_active else None


@dataclass
class VariantOption:
    variant: object
    price: object


def variant_options(product):
    return [VariantOption(v, line_price(product, v)) for v in product_variants(product)]


def product_images(product):
    return [
        img for img in (product.main_image, product.alt1_image, product.alt2_image, product.alt3_image) if img
    ]


def related(product, association_type, limit=8):
    """Active products linked from this one with the given type, in their admin order."""
    targets = [
        link.target_product
        for link in product.associations
        if link.association_type == association_type and link.is_active
    ]
    return [p for p in targets if p is not None and p.is_active and p.id != product.id][:limit]


def cross_sells(product, limit=8):
    return related(product, "XSELL", limit)


def upsells(product, limit=3):
    return related(product, "UPSELL", limit)


def similar(product, exclude=(), limit=4):
    """Fallback suggestions: other active products from the product's main category."""
    category = primary_category(product)
    if category is None:
        return []
    skip = {product.id, *(p.id for p in exclude)}
    return [p for p in category_products(category, "newest") if p.id not in skip][:limit]


def bag_suggestions(cart, limit=4):
    """Cross-sells of the items in the bag that aren't already in it."""
    if cart is None:
        return []
    in_bag = {item.product_id for item in cart.pending_items}
    suggestions = {}
    for item in cart.pending_items:
        if item.product is None:
            continue
        for product in cross_sells(item.product):
            if product.id not in in_bag:
                suggestions.setdefault(product.id, product)
    return list(suggestions.values())[:limit]


def home_page():
    """The active home page content (the newest if several are active)."""
    content = (
        db.session.query(HomePageContent)
        .filter(HomePageContent.is_active.is_(True))
        .order_by(HomePageContent.id.desc())
        .first()
    )
    if content is None:
        return HomePage()
    featured = []
    if content.category is not None and content.category.is_active:
        featured = active_products(content.category)
    return HomePage(
        hero_image=content.hero_image,
        slides=content.carousel.order_by(Carousel.id).all(),
        featured=featured,
        featured_title=content.category.name if featured else None,
    )


# ---------------------------------------------------------------- menu and category pages


def menu():
    """Top-level menu categories with their active children, cached for the request."""
    from flask import g

    if "shop_menu" not in g:
        top = (
            db.session.query(Category)
            .filter(
                Category.parent_id.is_(None), Category.is_active.is_(True), Category.show_in_menu.is_(True)
            )
            .order_by(Category.position, Category.id)
            .all()
        )
        g.shop_menu = [
            (category, [c for c in category.children if c.is_active and c.show_in_menu]) for category in top
        ]
    return g.shop_menu


def get_category(slug):
    category = db.session.query(Category).filter(Category.code == slug.upper()).first()
    return category if category is not None and category.is_active else None


def _with_children(category):
    return [category] + [c for c in category.children if c.is_active]


SORTS = {
    "featured": "Featured",
    "newest": "Newest",
    "price-asc": "Price: low to high",
    "price-desc": "Price: high to low",
}


def category_products(category, sort="featured"):
    """Active products in a category or its sub-categories, plus any price rule (e.g. Under $25)."""
    products = {}
    for cat in _with_children(category):
        for product in active_products(cat):
            products[product.id] = product
        if cat.max_price is not None:
            cheap = db.session.query(Product).filter(
                Product.is_active.is_(True), Product.sale_price <= cat.max_price
            )
            for product in cheap:
                products[product.id] = product
    items = list(products.values())
    if sort == "newest":
        items.sort(key=lambda p: -p.id)
    elif sort == "price-asc":
        items.sort(key=lambda p: (p.sale_price, p.id))
    elif sort == "price-desc":
        items.sort(key=lambda p: (-p.sale_price, p.id))
    else:
        items.sort(key=lambda p: p.id)
    return items


def search(query, limit=60):
    """Active products whose name, description, material, SKU or category matches every word."""
    words = [w for w in (query or "").split() if w][:6]
    if not words:
        return []
    q = db.session.query(Product).filter(Product.is_active.is_(True))
    for word in words:
        like = f"%{word}%"
        q = q.filter(
            Product.name.ilike(like)
            | Product.description.ilike(like)
            | Product.material.ilike(like)
            | Product.sku.ilike(like)
            | Product.categories.any(Category.name.ilike(like))
        )
    return q.order_by(Product.id).limit(limit).all()


def is_on_sale(product):
    return (
        product.retail_price is not None
        and product.sale_price is not None
        and product.retail_price > product.sale_price
    )


def new_arrivals(limit=8):
    category = get_category("NEW")
    items = category_products(category) if category else []
    return sorted(items, key=lambda p: -p.id)[:limit]


def products_in(code, limit=8):
    category = get_category(code)
    return category_products(category)[:limit] if category else []


PRODUCT_TYPES = ("EARRINGS", "NECKPIECES", "ACCESSORIES")


def primary_category(product):
    """The category to show in a product's breadcrumb: its type (e.g. Earrings > Jhumkas) if known."""
    categories = [c for c in product.categories if c.is_active]

    def rank(c):
        top = c.parent or c
        return (top.code not in PRODUCT_TYPES, c.parent is None, top.position, c.position)

    return min(categories, key=rank) if categories else None
