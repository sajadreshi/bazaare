from flask import abort, flash, redirect, request
from flask_admin import expose
from flask_admin.model.form import InlineFormAdmin
from flask_ckeditor import CKEditorField
from markupsafe import Markup
from wtforms import SelectField
from wtforms.validators import DataRequired

from app.adminapp.fields import StorageImageField
from app.adminapp.security import SecureModelView
from app.extension import db
from app.models import ASSOCIATION_TYPES, ORDER_STATUSES, Order, ProductAssociation, ProductAttribute, utcnow
from app.services import stock
from app.services.shipping import CARRIERS, HAND_DELIVERY
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
    """Kinds of product detail (Stone, Metal, Finish...). Values are set on each product's form."""

    column_list = ("name", "position", "products")
    column_labels = {"position": "Order", "products": "Products using it"}
    column_formatters = {"products": lambda v, c, m, n: len(m.product_links)}
    column_default_sort = [("position", False), ("name", False)]
    form_columns = ("name", "position")
    form_args = {
        "name": {"label": "Name (e.g. Stone, Metal, Finish, Length)"},
        "position": {"label": "Order on the product page (lowest first)", "default": 0},
    }


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


class ProductAttributeInline(InlineFormAdmin):
    """One row per product detail on the product form, e.g. Stone: Moonstone."""

    form_columns = ("id", "attribute", "value")
    form_label = "Details"
    form_args = {
        "attribute": {"label": "Attribute", "validators": [DataRequired()]},
        "value": {"label": "Value", "validators": [DataRequired()]},
    }


class ProductView(SecureModelView):
    form_extra_fields = {
        attr: StorageImageField(label, folder="products") for attr, label in PRODUCT_IMAGES.items()
    }
    form_excluded_columns = ["created_at", "updated_at", "attribute_links", "linked_from", "associations"]
    column_list = ("main_image", "sku", "name", "price", "compare_at_price", "categories", "is_active")
    column_labels = {
        "main_image": "Photo",
        "price": "Price",
        "compare_at_price": "Was",
        "is_active": "Active",
    }
    column_formatters = {
        **{attr: thumbnail(attr) for attr in PRODUCT_IMAGES},
        "compare_at_price": lambda v, c, m, n: m.compare_at_price if m.compare_at_price != m.price else "",
        "categories": lambda v, c, m, n: ", ".join(sorted(cat.name for cat in m.categories)),
    }
    column_default_sort = ("sku", False)
    column_searchable_list = ["name", "sku"]
    column_filters = ["price", "is_active"]
    # "Related products" table at the bottom of the product form.
    inline_models = (ProductAttributeInline(ProductAttribute), RelatedProductInline(ProductAssociation))


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


def order_customer(order):
    """(name, email, kind) for an order's buyer: the account if registered, else the shipping address."""
    customer = order.customer
    user = customer.user if customer else None
    if user is not None:
        return f"{user.first_name} {user.last_name}".strip(), user.email, "Registered"
    address = order.shipping_address or order.billing_address
    if address is not None:
        return f"{address.first_name} {address.last_name}".strip(), address.email, "Guest"
    return "Guest", None, "Guest"


def _status_badge(view, context, model, name):
    return Markup('<span class="bz-status bz-status--%s">%s</span>') % (
        model.status.lower(),
        model.status.title(),
    )


def _order_link(view, context, model, name):
    url = view.get_url(".details_view", id=model.id)
    return Markup('<a href="%s"><strong>%s</strong></a>') % (url, model.number)


def _customer_cell(view, context, model, name):
    person, email, kind = order_customer(model)
    return Markup("%s<br><small class='bz-muted'>%s · %s</small>") % (person, email or "no email", kind)


def _shipping_cell(view, context, model, name):
    if model.carrier == HAND_DELIVERY:
        return Markup("%s<br><small class='bz-muted'>Hand delivery</small>") % model.method.name
    if model.tracking_number:
        return Markup("%s<br><small class='bz-muted'>%s %s</small>") % (
            model.method.name,
            model.carrier or "",
            model.tracking_number,
        )
    return model.method.name


# Next steps offered as buttons on an order, depending on where it is now.
ORDER_ACTIONS = {
    "PLACED": [
        ("SHIPPED", "Mark shipped"),
        ("DELIVERED", "Delivered by hand"),
        ("CANCELLED", "Cancel order"),
    ],
    "SHIPPED": [("DELIVERED", "Mark delivered"), ("CANCELLED", "Cancel order")],
    "DELIVERED": [],
    "CANCELLED": [("PLACED", "Reopen")],
}


class OrderView(SecureModelView):
    """Orders come from checkout. Click one for the full picture; move it on with the status buttons."""

    can_create = False
    can_delete = False
    can_edit = False
    can_view_details = True
    details_template = "admin/order_details.html"
    column_default_sort = ("placed_at", True)
    column_list = ("number", "customer", "items", "total", "status", "shipping_method", "placed_at")
    column_labels = {"number": "Order", "shipping_method": "Shipping", "placed_at": "Placed"}
    column_formatters = {
        "number": _order_link,
        "customer": _customer_cell,
        "items": lambda v, c, m, n: sum(1 for _ in m.items),
        "total": lambda v, c, m, n: f"${m.total:.2f}",
        "status": _status_badge,
        "shipping_method": _shipping_cell,
        "placed_at": lambda v, c, m, n: f"{m.placed_at:%d %b %Y, %H:%M}",
    }
    column_sortable_list = ("total", "status", "shipping_method", "placed_at")
    column_filters = ("status", "shipping_method", "placed_at")
    column_searchable_list = ("id",)

    def render(self, template, **kwargs):
        if template == self.details_template and "model" in kwargs:
            order = kwargs["model"]
            kwargs.update(
                customer=order_customer(order),
                actions=ORDER_ACTIONS.get(order.status, []),
                carriers=list(CARRIERS),
                statuses=ORDER_STATUSES,
            )
        return super().render(template, **kwargs)

    @expose("/status/<int:order_id>", methods=["POST"])
    def set_status(self, order_id):
        order = db.session.get(Order, order_id)
        if order is None:
            abort(404)
        status = request.form.get("status", "")
        carrier = request.form.get("carrier", "").strip()
        tracking = request.form.get("tracking_number", "").strip()
        if status not in ORDER_STATUSES:
            flash("Unknown status.", "error")
        elif (
            status == "SHIPPED"
            and order.status != "SHIPPED"
            and not (carrier in CARRIERS and (tracking or carrier == HAND_DELIVERY))
        ):
            flash("To mark an order shipped, choose the carrier and enter the tracking number.", "error")
        elif status != order.status:
            previous = order.status
            order.status = status
            if status == "CANCELLED":
                stock.put_back(order)
            elif previous == "CANCELLED":
                stock.take_again(order)
            now = utcnow()
            if status == "SHIPPED":
                order.carrier, order.tracking_number = carrier, (tracking[:64] or None)
                order.shipped_at = now
            elif status == "DELIVERED":
                if carrier == HAND_DELIVERY and previous == "PLACED":
                    order.carrier, order.tracking_number = HAND_DELIVERY, None
                order.shipped_at = order.shipped_at or now
                order.delivered_at = now
            db.session.commit()
            flash(f"{order.number} moved from {previous.title()} to {status.title()}.", "success")
        return redirect(self.get_url(".details_view", id=order.id))
