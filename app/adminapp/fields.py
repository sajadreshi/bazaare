"""Admin form fields that upload images to app storage (R2 or the local fallback)."""

import json

from flask import render_template, request
from flask_admin.form.upload import ImageUploadField, ImageUploadInput
from markupsafe import Markup
from PIL import Image, UnidentifiedImageError
from wtforms import Field
from wtforms.validators import ValidationError

from app.storage import ALLOWED_FORMATS, image_url, save_image

ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp", "gif")
NOT_AN_IMAGE = "Please upload a JPEG, PNG, WebP or GIF image."


def check_image(file):
    """Raise ValidationError unless the upload is a JPEG, PNG, WebP or GIF we can open."""
    name = (file.filename or "").lower()
    if "." not in name or name.rsplit(".", 1)[1] not in ALLOWED_EXTENSIONS:
        raise ValidationError(NOT_AN_IMAGE)
    try:
        with Image.open(file.stream) as image:
            image.verify()
            if image.format not in ALLOWED_FORMATS:
                raise ValidationError(NOT_AN_IMAGE)
    except (UnidentifiedImageError, OSError) as error:
        raise ValidationError(f"{file.filename} isn't an image we can read.") from error
    finally:
        file.stream.seek(0)


class StorageImageInput(ImageUploadInput):
    data_template = (
        '<div class="image-thumbnail">'
        " <img %(image)s>"
        ' <label class="bz-remove-image"><input type="checkbox" name="%(marker)s"> Remove this image</label>'
        " <input %(text)s>"
        "</div>"
        "<input %(file)s>"
    )

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
        if self._is_uploaded_file(self.data):
            check_image(self.data)

    def populate_obj(self, obj, name):
        if self._should_delete:
            setattr(obj, name, None)
        elif self._is_uploaded_file(self.data):
            setattr(obj, name, save_image(self.data, self.folder))


class PhotosWidget:
    def __call__(self, field, **kwargs):
        return Markup(render_template("admin/_photos_field.html", field=field))


class PhotosField(Field):
    """A product's photo list: upload several at once, drag to reorder, star the main one, remove.

    The browser sends the wanted order as JSON in the field itself: storage keys of photos to
    keep and ``new:N`` for the Nth newly uploaded file (in ``<name>_new``). Removed photos only
    leave the product; their files stay in storage because past orders still show them.
    """

    widget = PhotosWidget()

    def __init__(self, label=None, validators=None, folder="products", model=None, **kwargs):
        super().__init__(label, validators, **kwargs)
        self.folder = folder
        self.model = model
        self.order = None
        self.new_files = []

    def process_formdata(self, valuelist):
        self.order = None
        raw = valuelist[0] if valuelist else ""
        if raw:
            try:
                order = json.loads(raw)
            except ValueError:
                order = None
            if isinstance(order, list) and all(isinstance(token, str) for token in order):
                self.order = order

    def pre_validate(self, form):
        self.new_files = [f for f in request.files.getlist(f"{self.name}_new") if f and f.filename]
        for file in self.new_files:
            check_image(file)

    @property
    def current(self):
        return list(self.object_data or [])

    def populate_obj(self, obj, name):
        existing = {photo.image: photo for photo in getattr(obj, name)}
        order = self.order
        if order is None:  # no script ran: keep what's there and add the uploads at the end
            order = list(existing) + [f"new:{i}" for i in range(len(self.new_files))]
        photos = []
        for token in order:
            if token.startswith("new:"):
                index = token[4:]
                if index.isdigit() and int(index) < len(self.new_files):
                    photos.append(self.model(image=save_image(self.new_files[int(index)], self.folder)))
            elif token in existing and existing[token] not in photos:
                photos.append(existing[token])
        for position, photo in enumerate(photos):
            photo.position = position
        setattr(obj, name, photos)
