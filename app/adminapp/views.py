from flask_admin.model.form import InlineFormAdmin
from flask_ckeditor import CKEditorField
from markupsafe import Markup
from wtforms import SelectField
from wtforms.validators import DataRequired

from app.adminapp.fields import StorageImageField
from app.adminapp.security import SecureModelView
from app.models import ASSOCIATION_TYPES, ORDER_STATUSES, ProductAssociation
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


class CarouselView(SecureModelView):
    """Slides in the home page's top banner. Every active slide shows, in order."""

    column_list = ("position", "image", "name", "header", "is_active", "updated_at")
    column_default_sort = [("position", False), ("id", False)]
    column_labels = {
        "position": "Order",
        "image": "Background",
        "header": "Headline",
        "is_active": "Active",
        "updated_at": "Updated",
    }
    column_formatters = {"image": thumbnail("image")}
    form_columns = ("name", "header", "text", "image", "position", "is_active")
    form_overrides = dict(text=CKEditorField)
    form_args = {
        "name": {"label": "Name (only shown in the admin)"},
        "header": {"label": "Headline"},
        "text": {"label": "Message"},
        "position": {"label": "Order (lowest first)", "default": 0},
        "is_active": {"label": "Active (shown on the home page)", "default": True},
    }
    form_extra_fields = {"image": StorageImageField("Background image (behind the headline)", folder="home")}


PRODUCT_IMAGES = {
    "main_image": "Main Image",
    "alt1_image": "Alternate Image 1",
    "alt2_image": "Alternate Image 2",
    "alt3_image": "Alternate Image 3",
}


ASSOCIATION_CHOICES = [(key, label) for key, label in ASSOCIATION_TYPES.items()]


class RelatedProductInline(InlineFormAdmin):
    """One row per related product on the product form: which product, what kind, order, on/off."""

    form_columns = ("id", "target_product", "association_type", "position", "is_active")
    form_label = "Related products"
    form_overrides = {"association_type": SelectField}
    form_args = {
        "target_product": {"label": "Product", "validators": [DataRequired()]},
        "association_type": {"label": "Show as", "choices": ASSOCIATION_CHOICES},
        "position": {"label": "Order", "default": 0},
        "is_active": {"label": "Active", "default": True},
    }


class ProductView(SecureModelView):
    column_formatters = {attr: thumbnail(attr) for attr in PRODUCT_IMAGES}
    form_extra_fields = {
        attr: StorageImageField(label, folder="products") for attr, label in PRODUCT_IMAGES.items()
    }
    form_excluded_columns = ["created_at", "updated_at", "attribute_links", "linked_from", "associations"]
    column_searchable_list = ["name", "sku"]
    column_filters = ["sale_price", "is_active"]
    # "Related products" table at the bottom of the product form.
    inline_models = (RelatedProductInline(ProductAssociation),)


class VariantView(SecureModelView):
    column_formatters = {"variant_image": thumbnail("variant_image")}
    form_extra_fields = {"variant_image": StorageImageField("Variant Image", folder="variants")}
    form_excluded_columns = ["created_at", "updated_at", "products"]
    column_display_pk = False


class ProductAssociationView(SecureModelView):
    """All related-product links in one list. They can also be edited on each product's form."""

    column_list = ("source_product", "association_type", "target_product", "position", "is_active")
    column_labels = {
        "source_product": "On the page of",
        "association_type": "Show as",
        "target_product": "Related product",
        "position": "Order",
        "is_active": "Active",
    }
    column_formatters = {
        "association_type": lambda v, c, m, n: ASSOCIATION_TYPES.get(m.association_type, m.association_type)
    }
    column_filters = ("association_type", "is_active")
    column_default_sort = [("source_product_id", False), ("association_type", False), ("position", False)]
    form_columns = ("source_product", "target_product", "association_type", "position", "is_active")
    form_choices = {"association_type": ASSOCIATION_CHOICES}
    form_args = {
        "source_product": {"label": "On the page of"},
        "target_product": {"label": "Related product"},
    }


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
