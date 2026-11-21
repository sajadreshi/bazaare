from flask_ckeditor import CKEditorField
from markupsafe import Markup

from app.adminapp.fields import StorageImageField
from app.adminapp.security import SecureModelView
from app.models import ORDER_STATUSES
from app.storage import image_url


def thumbnail(attr):
    """List-view column formatter showing an image's thumbnail."""

    def formatter(view, context, model, name):
        key = getattr(model, attr)
        if not key:
            return ""
        return Markup('<img src="%s" alt="" style="max-width:80px;max-height:80px">') % image_url(
            key, thumb=True
        )

    return formatter


class AttributesView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "product_links"]


class AttributesRelView(SecureModelView):
    column_display_pk = False
    column_list = ("product", "attribute")


def category_tree(categories):
    """[(category, depth)] in menu order: each parent followed by its children, by position."""
    by_parent = {}
    for category in categories:
        by_parent.setdefault(category.parent_id, []).append(category)
    for siblings in by_parent.values():
        siblings.sort(key=lambda c: (c.position or 0, c.name.lower()))
    ids = {c.id for c in categories}
    roots = [c for c in categories if c.parent_id is None or c.parent_id not in ids]
    roots.sort(key=lambda c: (c.parent_id is not None, not c.show_in_menu, c.position or 0, c.name.lower()))
    ordered = []

    def walk(category, depth):
        ordered.append((category, depth))
        for child in by_parent.get(category.id, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return ordered


class CategoryView(SecureModelView):
    """Categories shown as the menu tree: main menu items with their dropdown items indented below."""

    list_template = "admin/category_list.html"
    column_list = ("name", "code", "position", "show_in_menu", "is_active", "max_price", "products")
    column_labels = {
        "name": "Category",
        "show_in_menu": "In menu",
        "is_active": "Active",
        "max_price": "Price rule",
    }
    column_sortable_list = ()  # the tree order is the order
    column_searchable_list = ("name", "code")
    page_size = 500
    form_columns = (
        "name",
        "code",
        "description",
        "parent",
        "position",
        "show_in_menu",
        "is_active",
        "max_price",
        "banner_image",
        "product",
    )
    form_labels = {"product": "Products", "max_price": "Price rule (list all products at or below)"}
    form_extra_fields = {"banner_image": StorageImageField("Banner image", folder="banners")}
    form_args = {
        "parent": {"label": "Parent (empty = main menu item)"},
        "position": {"label": "Position in menu"},
    }

    def _format_name(view, context, model, name):
        depth = getattr(model, "_tree_depth", 0)
        prefix = Markup("&nbsp;&nbsp;&nbsp;&nbsp;" * depth + ("└─ " if depth else ""))
        label = Markup("<strong>%s</strong>") % model.name if depth == 0 else model.name
        return prefix + label

    def _format_products(view, context, model, name):
        return model.product.count()

    def _format_price_rule(view, context, model, name):
        return f"≤ ${model.max_price:.0f}" if model.max_price is not None else ""

    column_formatters = {"name": _format_name, "products": _format_products, "max_price": _format_price_rule}

    def get_list(self, page, sort_column, sort_desc, search, filters, execute=True, page_size=None):
        count, rows = super().get_list(None, None, False, search, filters, execute=True, page_size=None)
        rows = list(rows)
        tree = category_tree(rows)
        for category, depth in tree:
            category._tree_depth = depth
        return count, [category for category, _ in tree]


class CollectionView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "home"]
    column_display_pk = False


class CarouselView(SecureModelView):
    """A slide in the home page's top banner: a headline and a short message."""

    form_excluded_columns = ["created_at", "updated_at", "home"]
    column_list = ("name", "header", "updated_at")
    form_labels = {"name": "Name (admin only)", "header": "Headline", "text": "Message"}
    column_display_pk = False
    form_overrides = dict(text=CKEditorField)


class HomePageView(SecureModelView):
    """What the home page's top banner and Featured section show. The newest active row is used."""

    column_list = ("is_active", "hero_image", "carousel", "category", "updated_at")
    column_labels = {
        "is_active": "Active",
        "hero_image": "Banner image",
        "carousel": "Slides",
        "category": "Featured category",
        "updated_at": "Updated",
    }
    column_formatters = {
        "hero_image": thumbnail("hero_image"),
        "carousel": lambda v, c, m, n: ", ".join(s.name for s in m.carousel),
    }
    form_columns = ("is_active", "hero_image", "carousel", "category")
    form_args = {
        "is_active": {"label": "Active (the newest active row is shown on the home page)"},
        "carousel": {"label": "Slides (headline + message rotating in the top banner)"},
        "category": {"label": "Featured category (its products appear under the banner)"},
    }
    form_extra_fields = {"hero_image": StorageImageField("Banner image (behind the slides)", folder="home")}
    column_display_pk = False


PRODUCT_IMAGES = {
    "main_image": "Main Image",
    "alt1_image": "Alternate Image 1",
    "alt2_image": "Alternate Image 2",
    "alt3_image": "Alternate Image 3",
}


class ProductView(SecureModelView):
    column_formatters = {attr: thumbnail(attr) for attr in PRODUCT_IMAGES}
    form_extra_fields = {
        attr: StorageImageField(label, folder="products") for attr, label in PRODUCT_IMAGES.items()
    }
    form_excluded_columns = ["created_at", "updated_at", "attribute_links"]
    column_searchable_list = ["name", "sku"]
    column_filters = ["sale_price"]
    edit_modal = True


class VariantView(SecureModelView):
    column_formatters = {"variant_image": thumbnail("variant_image")}
    form_extra_fields = {"variant_image": StorageImageField("Variant Image", folder="variants")}
    form_excluded_columns = ["created_at", "updated_at", "products"]
    column_display_pk = False


class ProductAssociationView(SecureModelView):
    column_display_pk = False  # optional, but I like to see the IDs in the list
    column_list = ("source_product", "target_product", "is_active", "association_type")


class UserView(SecureModelView):
    """
    @listens_for(User.password, 'set', retval=True)
    def hash_user_password(target, value, oldvalue, initiator):
        if value != oldvalue:
            return generate_password_hash(value)
        return value
    """

    column_searchable_list = ["email", "last_name"]
    column_filters = ["email"]
    column_exclude_list = ["password", "created_at"]
    form_excluded_columns = ["created_at", "updated_at"]
    column_display_pk = False


class RoleView(SecureModelView):
    column_display_pk = False


class HolidayView(SecureModelView):
    column_display_pk = False


class OrderView(SecureModelView):
    """Orders are created by checkout; admins can only move them through their statuses."""

    can_create = False
    can_delete = False
    column_default_sort = ("placed_at", True)
    column_list = ("id", "status", "customer_id", "total", "delivery_date", "delivery_window", "placed_at")
    column_filters = ("status", "placed_at")
    column_searchable_list = ("id",)
    form_columns = ("status",)
    form_choices = {"status": [(s, s.title()) for s in ORDER_STATUSES]}


class OrderItemView(SecureModelView):
    can_create = False
    can_edit = False
    can_delete = False
    column_list = ("order", "sku", "name", "variant_name", "price", "shipping", "tax", "discount")
    column_filters = ("order_id", "sku")
