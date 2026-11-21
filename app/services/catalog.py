"""Reading the catalog: collections, categories, products and the home page.

Only active collections, categories and products are ever shown to shoppers.
"""

from dataclasses import dataclass, field

from app.extension import db
from app.models import Carousel, Category, Collection, HomePageContent, Product, ProductAssociation
from app.services.cart import line_price, product_variants


@dataclass
class CategoryShelf:
    """An active category with its active products, ready to render as a grid."""

    category: Category
    products: list


@dataclass
class HomePage:
    hero_image: str | None = None
    slides: list = field(default_factory=list)
    featured: list = field(default_factory=list)
    shelves: list = field(default_factory=list)


def active_products(category):
    return category.product.filter(Product.is_active.is_(True)).order_by(Product.id).all()


def shelves_for(collection):
    """Active categories of a collection that have at least one active product."""
    if collection is None or not collection.is_active:
        return []
    categories = collection.category.filter(Category.is_active.is_(True)).order_by(Category.id).all()
    shelves = [CategoryShelf(category, active_products(category)) for category in categories]
    return [shelf for shelf in shelves if shelf.products]


def collection_shelves():
    """Every active collection's shelves, merged (one shelf per category)."""
    shelves, seen = [], set()
    for collection in (
        db.session.query(Collection).filter(Collection.is_active.is_(True)).order_by(Collection.id)
    ):
        for shelf in shelves_for(collection):
            if shelf.category.id not in seen:
                seen.add(shelf.category.id)
                shelves.append(shelf)
    return shelves


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


def cross_sells(product):
    links = (
        db.session.query(ProductAssociation)
        .filter_by(source_product_id=product.id, association_type="XSELL", is_active=True)
        .order_by(ProductAssociation.id)
    )
    return [link.target_product for link in links if link.target_product and link.target_product.is_active]


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
        shelves=shelves_for(content.collection),
    )
