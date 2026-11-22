import re
from decimal import Decimal

from flask import abort, flash, redirect, request, url_for
from flask_admin import expose
from flask_admin.model.form import InlineFormAdmin
from flask_ckeditor import CKEditorField
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup
from wtforms import HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, ValidationError

from app.adminapp.fields import PhotosField, StorageImageField
from app.adminapp.security import SecureModelView
from app.extension import db
from app.models import (
    ASSOCIATION_TYPES,
    ORDER_STATUSES,
    Category,
    Coupon,
    Order,
    Product,
    ProductAssociation,
    ProductAttribute,
    ProductImage,
    Variant,
    utcnow,
)
from app.richtext import clean_html
from app.services import inventory, stock
from app.services.catalog import category_products
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


def _categories_as_tree():
    tree = category_tree(Category.query.all())
    for category, depth in tree:
        category._tree_depth = depth
    return [category for category, _ in tree]


class CategoryView(SecureModelView):
    """Categories shown as the menu tree: main menu items with their dropdown items indented below."""

    list_template = "admin/category_list.html"
    column_list = ("order", "name", "products", "show_in_menu", "is_active", "tools")
    column_labels = {
        "order": "",
        "name": "Category",
        "show_in_menu": "In menu",
        "is_active": "Active",
        "tools": "",
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
    form_labels = {"name": "Name", "product": "Picked products", "max_price": "Price rule: up to ($)"}
    form_overrides = {"description": TextAreaField}
    form_extra_fields = {"banner_image": StorageImageField("Banner image", folder="banners")}
    form_args = {
        "name": {"label": "Name", "description": "Shown in the menu and as the page title."},
        "product": {"label": "Picked products"},
        "max_price": {"label": "Price rule: up to ($)"},
        "parent": {
            "label": "Parent",
            "description": "Empty = a main menu item. Otherwise it appears in that item's dropdown.",
            "query_factory": lambda: _categories_as_tree(),
            "get_label": lambda c: ("— " * getattr(c, "_tree_depth", 0)) + c.name,
        },
        "position": {"label": "Position in menu", "default": 0},
        "description": {"render_kw": {"rows": 3}},
        "show_in_menu": {"label": "Show in the menu"},
        "is_active": {"label": "Active (page can be visited)", "default": True},
    }
    edit_template = "admin/category_edit.html"
    create_template = "admin/category_create.html"

    def scaffold_form(self):
        form_class = super().scaffold_form()
        code = StringField(
            "Code (used in the page address)",
            validators=[Optional(), Length(max=64)],
            description="Leave empty to make one from the name.",
        )
        code.creation_counter = form_class.code.creation_counter  # keep its place, after the name
        form_class.code = code
        return form_class

    def on_model_change(self, form, model, is_created):
        code = re.sub(r"[^A-Z0-9]+", "-", (model.code or model.name or "").upper()).strip("-")
        if model.code:
            clash = _taken(Category, "code", code, exclude_id=model.id)
            if clash is not None:
                raise ValidationError(f"Code {code} is already used by {clash.name}.")
        else:
            code = unique_value(Category, "code", code or "CATEGORY", exclude_id=model.id)
        model.code = code
        parent = model.parent
        while parent is not None:
            if parent is model:
                raise ValidationError("A category can't be inside itself or one of its own sub-categories.")
            parent = parent.parent

    def create_form(self, obj=None):
        form = super().create_form(obj)
        # "+ Sub-category" links pass the parent along.
        parent_id = request.args.get("parent", type=int)
        if request.method == "GET" and parent_id:
            form.parent.data = db.session.get(Category, parent_id)
        return form

    def _format_order(view, context, model, name):
        def arrow(direction, symbol, label):
            return Markup(
                '<form method="post" action="%s" class="bz-inline-form">'
                '<input type="hidden" name="csrf_token" value="%s">'
                '<button type="submit" class="bz-arrow" title="%s">%s</button></form>'
            ) % (view.get_url(".move", id=model.id, direction=direction), generate_csrf(), label, symbol)

        return Markup('<div class="bz-arrows">%s%s</div>') % (
            arrow("up", "↑", "Move up"),
            arrow("down", "↓", "Move down"),
        )

    def _format_name(view, context, model, name):
        depth = getattr(model, "_tree_depth", 0)
        edit = view.get_url(".edit_view", id=model.id, url=request.url)
        label = Markup('<a href="%s" class="bz-tree__name bz-tree__name--%d">%s</a>') % (
            edit,
            min(depth, 2),
            model.name,
        )
        rule = (
            Markup(' <span class="bz-tag">≤ $%.0f</span>') % model.max_price
            if model.max_price is not None
            else ""
        )
        indent = Markup('<span class="bz-tree__indent" style="width:%dpx"></span>') % (depth * 26)
        branch = Markup('<span class="bz-tree__branch">└</span>') if depth else ""
        return Markup('<div class="bz-tree">%s%s%s%s</div>') % (indent, branch, label, rule)

    def _format_products(view, context, model, name):
        picked = model.product.count()
        shown = len(category_products(model)) if model.is_active else 0
        if shown == picked:
            return picked
        return Markup('%d <small class="bz-muted">(%d in shop)</small>') % (picked, shown)

    def _format_flag(view, context, model, name):
        on = getattr(model, name)
        return Markup('<span class="bz-dot %s">%s</span>') % ("is-on" if on else "", "Yes" if on else "No")

    def _format_tools(view, context, model, name):
        return Markup(
            '<a class="bz-link-btn" href="%s">+ Sub-category</a>'
            '<a class="bz-link-btn" href="%s" target="_blank" rel="noopener">View ↗</a>'
        ) % (
            view.get_url(".create_view", parent=model.id, url=request.url),
            url_for("catalog.category", slug=model.slug),
        )

    column_formatters = {
        "order": _format_order,
        "name": _format_name,
        "products": _format_products,
        "show_in_menu": _format_flag,
        "is_active": _format_flag,
        "tools": _format_tools,
    }

    @expose("/move/<int:id>/<direction>", methods=["POST"])
    def move(self, id, direction):
        """Swap a category with its neighbour among its siblings, then renumber them 0, 10, 20..."""
        category = db.session.get(Category, id) or abort(404)
        siblings = Category.query.filter(
            Category.parent_id.is_(None)
            if category.parent_id is None
            else Category.parent_id == category.parent_id
        ).all()
        if category.parent_id is None:  # main menu items and hidden top-level pages sort separately
            siblings = [c for c in siblings if c.show_in_menu == category.show_in_menu]
        siblings.sort(key=lambda c: (c.position or 0, c.name.lower()))
        index = siblings.index(category)
        other = index - 1 if direction == "up" else index + 1
        if 0 <= other < len(siblings):
            siblings[index], siblings[other] = siblings[other], siblings[index]
        for position, sibling in enumerate(siblings):
            sibling.position = position * 10
        db.session.commit()
        return redirect(self.get_url(".index_view"))

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


ASSOCIATION_CHOICES = [(key, label) for key, label in ASSOCIATION_TYPES.items()]


def _optional_decimal(label):
    return {"label": label, "validators": [Optional(), NumberRange(min=0)]}


class OptionInline(InlineFormAdmin):
    """The product's sizes/designs as table rows: name, own price, stock, photo, default."""

    form_columns = ("id", "name", "price", "stock", "variant_image", "is_default", "position")
    form_label = "Option"
    form_overrides = {"position": HiddenField}
    form_args = {
        "name": {"label": "Option", "validators": [DataRequired()], "description": "e.g. Ring size 7"},
        "price": {**_optional_decimal("Price"), "description": "Same as product"},
        "stock": {
            "label": "Stock",
            "validators": [InputRequired("How many do you have?"), NumberRange(min=0)],
            "description": "How many",
        },
        "is_default": {"label": "Default"},
    }
    form_extra_fields = {"variant_image": StorageImageField("Photo", folder="variants")}


class RelatedProductInline(InlineFormAdmin):
    """One row per related product on the product form: which product, what kind, on/off."""

    form_columns = ("id", "target_product", "association_type", "is_active", "position")
    form_label = "Related product"
    form_overrides = {"association_type": SelectField, "position": HiddenField}
    form_args = {
        "target_product": {"label": "Product", "validators": [DataRequired()]},
        "association_type": {"label": "Show as", "choices": ASSOCIATION_CHOICES},
        "is_active": {"label": "Active", "default": True},
    }


class ProductAttributeInline(InlineFormAdmin):
    """One row per product detail on the product form, e.g. Stone: Moonstone."""

    form_columns = ("id", "attribute", "value")
    form_label = "Detail"
    form_args = {
        "attribute": {"label": "Attribute", "validators": [DataRequired()]},
        "value": {"label": "Value", "validators": [DataRequired()], "description": "e.g. Moonstone"},
    }


def sku_from_name(name):
    """BZ- plus up to three words of the name, four letters each, e.g. BZ-PEAC-EMER-PEAR."""
    words = re.sub(r"[^A-Z0-9 ]+", " ", (name or "").upper()).split()
    return "-".join(["BZ", *(word[:4] for word in words[:3])])


def unique_value(model, column, base, exclude_id=None, limit=64):
    """``base``, or ``base-2``, ``base-3``... whichever isn't used yet by another row."""
    candidate, n = base[:limit], 1
    while True:
        if not _taken(model, column, candidate, exclude_id):
            return candidate
        n += 1
        suffix = f"-{n}"
        candidate = base[: limit - len(suffix)] + suffix


def _taken(model, column, value, exclude_id=None):
    """The other row already using this value, if any (without flushing the row being saved)."""
    with db.session.no_autoflush:
        query = model.query.filter(getattr(model, column) == value)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        return query.first()


def _photo_cell(view, context, model, name):
    if not model.main_image:
        return Markup('<span class="bz-nophoto" title="No photo">—</span>')
    return Markup('<img class="bz-list-thumb" src="%s" alt="">') % image_url(model.main_image, thumb=True)


def _name_cell(view, context, model, name):
    edit = view.get_url(".edit_view", id=model.id, url=request.url)
    shop = url_for("catalog.product", productId=model.id)
    return Markup(
        '<a href="%s"><strong>%s</strong></a><br><small class="bz-muted">%s · '
        '<a href="%s" target="_blank" rel="noopener">view in shop ↗</a></small>'
    ) % (edit, model.name, model.sku, shop)


def _price_cell(view, context, model, name):
    text = Markup("$%.2f") % model.price
    if model.on_sale:
        text += Markup(' <s class="bz-muted">$%.2f</s>') % model.compare_at_price
    return text


def _stock_cell(view, context, model, name):
    options = model.options
    if not options:
        return Markup('<span class="bz-pill bz-pill--warn">no options</span>')
    if all(o.stock is None for o in options):
        return Markup('<span class="bz-pill bz-pill--bad">stock not set · can\'t be sold</span>')
    if model.sold_out_at is not None:
        return Markup(
            '<span class="bz-pill bz-pill--bad">sold out · hidden</span>'
            '<br><small class="bz-muted">since %s</small>'
        ) % (f"{model.sold_out_at:%d %b}")
    available = sum(o.available for o in options)
    sold_out = [o for o in options if not o.in_stock]
    if not available:
        return Markup('<span class="bz-pill bz-pill--bad">sold out</span>')
    label = Markup("%d available") % available
    if available <= inventory.low_stock_alert():
        label = Markup('<span class="bz-pill bz-pill--warn">%d left</span>') % available
    if sold_out:
        label += Markup('<br><small class="bz-muted">%d option(s) sold out or not counted</small>') % len(
            sold_out
        )
    return label


def _active_cell(view, context, model, name):
    action = view.get_url(".toggle_active", id=model.id)
    return Markup(
        '<form method="post" action="%s" class="bz-inline-form">'
        '<input type="hidden" name="csrf_token" value="%s">'
        '<input type="hidden" name="next" value="%s">'
        '<button type="submit" class="bz-switch %s" title="%s"><span></span>%s</button></form>'
    ) % (
        action,
        generate_csrf(),
        request.full_path,
        "is-on" if model.is_active else "",
        "Click to hide from the shop" if model.is_active else "Click to show in the shop",
        "Active" if model.is_active else "Hidden",
    )


class ProductView(SecureModelView):
    """Products, edited on one sectioned page: basics, photos, pricing, options & stock, details, related."""

    create_template = "admin/product_create.html"
    edit_template = "admin/product_edit.html"
    form_columns = (
        "name",
        "sku",
        "description",
        "material",
        "is_handmade",
        "price",
        "compare_at_price",
        "option_label",
        "is_active",
        "categories",
        "images",
        "options",
        "attribute_links",
        "associations",
    )
    form_overrides = {"description": TextAreaField}
    form_args = {
        "name": {"label": "Name", "validators": [DataRequired(), Length(max=150)]},
        "description": {"label": "Description", "render_kw": {"data-bz-rich": "1", "rows": 6}},
        "material": {"label": "Material"},
        "is_handmade": {"label": "Handmade"},
        "price": {"label": "Price ($)", "validators": [NumberRange(min=0)]},
        "compare_at_price": _optional_decimal("Compare-at price ($)"),
        "option_label": {"label": "Option name"},
        "is_active": {"label": "Active (shown in the shop)"},
        "categories": {"label": "Categories"},
    }
    form_extra_fields = {"images": PhotosField("Photos", folder="products", model=ProductImage)}
    inline_models = (
        OptionInline(Variant),
        ProductAttributeInline(ProductAttribute),
        RelatedProductInline(ProductAssociation),
    )

    column_list = ("photo", "name", "price", "stock", "categories", "is_active")
    column_labels = {"photo": "", "name": "Product", "is_active": "Shown"}
    column_formatters = {
        "photo": _photo_cell,
        "name": _name_cell,
        "price": _price_cell,
        "stock": _stock_cell,
        "is_active": _active_cell,
        "categories": lambda v, c, m, n: ", ".join(sorted(cat.name for cat in m.categories)),
    }
    column_sortable_list = ("name", "price", "is_active")
    column_default_sort = ("name", False)
    column_searchable_list = ["name", "sku"]
    column_filters = ["price", "is_active", "categories.name"]
    page_size = 50

    def scaffold_form(self):
        form_class = super().scaffold_form()
        # Optional here: an empty SKU is made from the name when saving.
        form_class.sku = StringField("SKU", validators=[Optional(), Length(max=64)])
        return form_class

    def on_model_change(self, form, model, is_created):
        model.description = clean_html(model.description) or None
        sku = (model.sku or "").strip().upper()
        if sku:
            clash = _taken(Product, "sku", sku, exclude_id=model.id)
            if clash is not None:
                raise ValidationError(f"SKU {sku} is already used by {clash.name}.")
        else:
            sku = unique_value(Product, "sku", sku_from_name(model.name), exclude_id=model.id)
        model.sku = sku
        if model.compare_at_price is not None and model.compare_at_price <= model.price:
            model.compare_at_price = None
        if not model.options:
            raise ValidationError(
                "Add the stock: at least one row under Options & stock "
                "(use “One Size” if there's just one kind)."
            )
        defaults = [o for o in model.options if o.is_default]
        for option in model.options:
            option.is_default = option is (defaults[0] if defaults else model.options[0])
        for rows in (model.options, model.associations):
            for row in rows:
                row.position = int(row.position) if str(row.position or "").isdigit() else 0
        # Visibility: an admin un-ticking Active hides it for good (no automatic comeback);
        # otherwise the product is hidden when it sells out and comes back when restocked.
        was_active = form.is_active.object_data
        if not model.is_active and (is_created or was_active):
            model.sold_out_at = None
        if model.is_active and not was_active:
            model.sold_out_at = None
        hidden, restored = inventory.refresh([model])
        if hidden:
            flash(
                f"{model.name} has no stock to sell, so it's hidden from the shop until you add some.",
                "warning",
            )
        if restored:
            flash(f"{model.name} is back in stock and showing in the shop again.", "success")

    @expose("/toggle/<int:id>", methods=["POST"])
    def toggle_active(self, id):
        product = db.session.get(Product, id) or abort(404)
        if not product.is_active and inventory.is_sold_out(product):
            flash(
                f"{product.name} is sold out. Add stock to its options first, then it shows again.", "error"
            )
        else:
            product.is_active = not product.is_active
            product.sold_out_at = None
            db.session.commit()
            where = "shown in" if product.is_active else "hidden from"
            flash(f"{product.name} is now {where} the shop.", "success")
        back = request.form.get("next", "")
        return redirect(back if back.startswith("/admin/") else self.get_url(".index_view"))

    @expose("/duplicate/<int:id>", methods=["POST"])
    def duplicate(self, id):
        source = db.session.get(Product, id) or abort(404)
        with db.session.no_autoflush:
            copy = duplicate_product(source)
        db.session.commit()
        flash(f"Copied {source.name}. The copy is hidden until you tick Active; set its stock.", "success")
        return redirect(self.get_url(".edit_view", id=copy.id))


def duplicate_product(source):
    """A hidden copy of a product with its photos, options (stock 0 if counted), details and links."""
    copy = Product(
        sku=unique_value(Product, "sku", f"{source.sku}-COPY"),
        name=f"{source.name} (copy)"[:150],
        description=source.description,
        price=source.price,
        compare_at_price=source.compare_at_price,
        material=source.material,
        is_handmade=source.is_handmade,
        option_label=source.option_label,
        is_active=False,
    )
    db.session.add(copy)
    copy.categories = list(source.categories)
    copy.images = [ProductImage(image=p.image, position=p.position) for p in source.images]
    copy.options = [
        Variant(
            name=o.name,
            price=o.price,
            stock=None if o.stock is None else 0,
            is_default=o.is_default,
            position=o.position,
            weight=o.weight,
            variant_image=o.variant_image,
        )
        for o in source.options
    ]
    copy.attribute_links = [
        ProductAttribute(attribute=a.attribute, value=a.value) for a in source.attribute_links
    ]
    copy.associations = [
        ProductAssociation(
            target_product=a.target_product,
            association_type=a.association_type,
            position=a.position,
            is_active=a.is_active,
        )
        for a in source.associations
    ]
    return copy


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
    """Days the shop doesn't ship. Delivery estimates (checkout, order pages) skip them, like weekends."""

    column_display_pk = False
    column_list = ("holiday_date",)
    column_labels = {"holiday_date": "Date"}
    column_default_sort = ("holiday_date", False)
    column_formatters = {
        "holiday_date": lambda v, c, m, n: f"{m.holiday_date:%A %d %B %Y}" if m.holiday_date else ""
    }
    form_args = {
        "holiday_date": {
            "label": "Date",
            "description": "A day you don't ship. Delivery estimates skip it, like weekends.",
        }
    }
    list_template = "admin/holiday_list.html"


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


def _coupon_offer(view, context, model, name):
    return Markup("<strong>%s</strong>") % model.offer


def _coupon_conditions(view, context, model, name):
    parts = []
    if model.min_order:
        parts.append(f"bag ${model.min_order:.2f}+")
    if model.starts_at or model.ends_at:
        start = f"{model.starts_at:%d %b}" if model.starts_at else "now"
        end = f"{model.ends_at:%d %b %Y}" if model.ends_at else "no end"
        parts.append(f"{start} → {end}")
    return ", ".join(parts) or Markup('<span class="bz-muted">any order</span>')


def _coupon_uses(view, context, model, name):
    limit = f" / {model.max_uses}" if model.max_uses is not None else ""
    return f"{model.times_used}{limit}"


def _coupon_state(view, context, model, name):
    from app.services import promotions

    reason = promotions.problem(model, merchandise=Decimal("1e9"))
    if reason is None:
        return Markup('<span class="bz-dot is-on">Live</span>')
    label = "Off" if not model.is_active else reason.replace(f"{model.code} ", "").rstrip(".").capitalize()
    return Markup('<span class="bz-dot">%s</span>') % label


class CouponView(SecureModelView):
    """Coupon codes shoppers type at checkout: % or $ off, with optional minimum, dates and use limit."""

    column_list = ("code", "offer", "conditions", "uses", "state", "description")
    column_labels = {
        "offer": "Gives",
        "conditions": "When",
        "uses": "Used",
        "state": "Status",
        "description": "Note",
    }
    column_formatters = {
        "offer": _coupon_offer,
        "conditions": _coupon_conditions,
        "uses": _coupon_uses,
        "state": _coupon_state,
    }
    column_searchable_list = ("code", "description")
    column_default_sort = ("created_at", True)
    form_columns = (
        "code",
        "kind",
        "value",
        "min_order",
        "starts_at",
        "ends_at",
        "max_uses",
        "is_active",
        "description",
    )
    form_overrides = {"kind": SelectField}
    form_args = {
        "code": {
            "label": "Code",
            "description": "What shoppers type, e.g. DIWALI15. Letters and numbers; case doesn't matter.",
            "validators": [DataRequired(), Length(max=40)],
        },
        "kind": {
            "label": "Type",
            "choices": [("PERCENT", "Percentage off the order"), ("AMOUNT", "Dollar amount off the order")],
        },
        "value": {
            "label": "Amount",
            "description": "15 = 15% off (percentage) or $15 off (dollar amount).",
            "validators": [DataRequired(), NumberRange(min=0.01)],
        },
        "min_order": {
            **_optional_decimal("Minimum bag ($)"),
            "description": "Optional. Only works when the bag is at least this.",
        },
        "starts_at": {"label": "Starts", "description": "Optional. Leave empty to start now."},
        "ends_at": {"label": "Ends", "description": "Optional. Leave empty for no end date."},
        "max_uses": {
            "label": "Total uses allowed",
            "description": "Optional. e.g. 100 for the first 100 orders. Empty = unlimited.",
            "validators": [Optional(), NumberRange(min=1)],
        },
        "is_active": {"label": "Active", "default": True},
        "description": {
            "label": "Note (only for you)",
            "description": "e.g. Diwali newsletter, Instagram giveaway.",
        },
    }

    def on_model_change(self, form, model, is_created):
        model.code = re.sub(r"[^A-Z0-9_-]", "", (model.code or "").upper())
        if not model.code:
            raise ValidationError("The code needs letters or numbers.")
        clash = _taken(Coupon, "code", model.code, exclude_id=model.id)
        if clash is not None:
            raise ValidationError(f"There's already a coupon called {model.code}.")
        if model.kind == "PERCENT" and model.value > 100:
            raise ValidationError("A percentage can't be more than 100.")
        if model.starts_at and model.ends_at and model.ends_at <= model.starts_at:
            raise ValidationError("The end date must be after the start date.")
