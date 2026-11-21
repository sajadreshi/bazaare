import os
import os.path as op

from flask import url_for
from flask_admin import form
from flask_ckeditor import CKEditorField
from markupsafe import Markup
from sqlalchemy.event import listens_for

from app.adminapp.security import SecureModelView
from app.models import ORDER_STATUSES, HomePageContent, Product, Variant

# Create directory for file fields to use
images_dir = "images/"
image_path = op.join(op.dirname(__file__), "../static/images")
try:
    os.mkdir(image_path)
except OSError:
    pass


# Product Model Start
def remove_image_from_dir(targetPath):
    if targetPath:
        # remove main image
        try:
            os.remove(op.join(image_path, targetPath))
        except OSError:
            pass
        # remove thumbnail
        try:
            os.remove(op.join(image_path, form.thumbgen_filename(targetPath)))
        except OSError:
            pass


# Attribute Model Start
class AttributesView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "product_links"]


# Attribute Relationship view
class AttributesRelView(SecureModelView):
    column_display_pk = False  # optional, but I like to see the IDs in the list
    column_list = ("product", "attribute")


# Attribute Model Start
class CategoryView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "collection", "home"]


class CollectionView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "home"]
    column_display_pk = False


class CarouselView(SecureModelView):
    form_excluded_columns = ["created_at", "updated_at", "home"]
    column_display_pk = False
    form_overrides = dict(text=CKEditorField)


class HomePageView(SecureModelView):
    @listens_for(HomePageContent, "after_delete")
    def del_image(mapper, connection, target):
        if target.hero_image:
            remove_image_from_dir(target.hero_image)

    def _list_thumbnail_hero_image(view, context, model, name):
        if not model.hero_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.hero_image)))
        )

    column_formatters = {"hero_image": _list_thumbnail_hero_image}

    form_extra_fields = {
        "hero_image": form.ImageUploadField(
            "Hero Image", base_path=image_path, thumbnail_size=(100, 100, True)
        )
    }
    form_excluded_columns = ["home", "created_at", "updated_at"]
    column_display_pk = False


class ProductView(SecureModelView):
    @listens_for(Product, "after_delete")
    def del_image(mapper, connection, target):
        if target.main_image:
            remove_image_from_dir(target.main_image)
        if target.alt1_image:
            remove_image_from_dir(target.alt1_image)
        if target.alt2_image:
            remove_image_from_dir(target.alt2_image)
        if target.alt3_image:
            remove_image_from_dir(target.alt3_image)

    def _list_thumbnail_main(view, context, model, name):
        if not model.main_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.main_image)))
        )

    def _list_thumbnail_alt1(view, context, model, name):
        if not model.alt1_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.alt1_image)))
        )

    def _list_thumbnail_alt2(view, context, model, name):
        if not model.alt2_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.alt2_image)))
        )

    def _list_thumbnail_alt3(view, context, model, name):
        if not model.alt3_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.alt3_image)))
        )

    column_formatters = {
        "main_image": _list_thumbnail_main,
        "alt1_image": _list_thumbnail_alt1,
        "alt2_image": _list_thumbnail_alt2,
        "alt3_image": _list_thumbnail_alt3,
    }

    # Alternative way to contribute field is to override it completely.
    # In this case, Flask-Admin won't attempt to merge various parameters for the field.
    form_extra_fields = {
        "main_image": form.ImageUploadField(
            "Main Image", base_path=image_path, thumbnail_size=(100, 100, True)
        ),
        # Alternate Image 1
        "alt1_image": form.ImageUploadField(
            "Alternate Image1", base_path=image_path, thumbnail_size=(100, 100, True)
        ),
        # Alternate Image 2
        "alt2_image": form.ImageUploadField(
            "Alternate Image2", base_path=image_path, thumbnail_size=(100, 100, True)
        ),
        # Alternate Image 3
        "alt3_image": form.ImageUploadField(
            "Alternate Image3", base_path=image_path, thumbnail_size=(100, 100, True)
        ),
    }

    form_excluded_columns = ["created_at", "updated_at", "categories", "attribute_links"]
    column_searchable_list = ["name", "sku"]
    column_filters = ["sale_price"]
    edit_modal = True


class VariantView(SecureModelView):
    @listens_for(Variant, "after_delete")
    def del_image(mapper, connection, target):
        if target.variant_image:
            remove_image_from_dir(target.variant_image)

    def _list_thumbnail_variant_image(view, context, model, name):
        if not model.variant_image:
            return ""

        return Markup(
            '<img src="%s">'
            % url_for("static", filename=form.thumbgen_filename(op.join(images_dir, model.variant_image)))
        )

    column_formatters = {"variant_image": _list_thumbnail_variant_image}

    form_extra_fields = {
        "variant_image": form.ImageUploadField(
            "Variant Image", base_path=image_path, thumbnail_size=(100, 100, True)
        )
    }
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
