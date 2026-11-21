"""Admin form field that uploads images to app storage (R2 or the local fallback)."""

from flask_admin.form.upload import ImageUploadField, ImageUploadInput
from PIL import Image, UnidentifiedImageError
from wtforms.validators import ValidationError

from app.storage import ALLOWED_FORMATS, image_url, save_image

ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif")


class StorageImageInput(ImageUploadInput):
    def get_url(self, field):
        return image_url(field.data, thumb=True)


class StorageImageField(ImageUploadField):
    """Like Flask-Admin's ImageUploadField, but files go to app storage under unique keys.

    Replacing or removing an image only changes the product; the stored files are
    kept, because past orders still show them.
    """

    widget = StorageImageInput()

    def __init__(self, label=None, validators=None, folder="products", **kwargs):
        super().__init__(
            label, validators, base_path="/unused", allowed_extensions=ALLOWED_EXTENSIONS, **kwargs
        )
        self.folder = folder

    def pre_validate(self, form):
        if not self._is_uploaded_file(self.data):
            return
        if not self.is_file_allowed(self.data.filename):
            raise ValidationError("Please upload a JPEG, PNG, WebP or GIF image.")
        try:
            with Image.open(self.data.stream) as image:
                image.verify()
                if image.format not in ALLOWED_FORMATS:
                    raise ValidationError("Please upload a JPEG, PNG, WebP or GIF image.")
        except (UnidentifiedImageError, OSError) as error:
            raise ValidationError("That file isn't an image we can read.") from error
        finally:
            self.data.stream.seek(0)

    def populate_obj(self, obj, name):
        if self._should_delete:
            setattr(obj, name, None)
        elif self._is_uploaded_file(self.data):
            setattr(obj, name, save_image(self.data, self.folder))
