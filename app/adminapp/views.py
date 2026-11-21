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
    column_formatters = {"hero_image": thumbnail("hero_image")}
    form_extra_fields = {"hero_image": StorageImageField("Hero Image", folder="home")}
    form_excluded_columns = ["home", "created_at", "updated_at"]
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
