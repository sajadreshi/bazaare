"""Where uploaded images live: a Cloudflare R2 bucket, or a local folder as a fallback.

Uploads are stored under unique keys such as ``products/2026/11/3f2a….jpg`` and
are never overwritten, so they can be cached forever. The database stores only
the key; ``image_url()`` turns it into the public URL.

R2 is used when all R2_* settings are present (see .env.example). Otherwise
files go to UPLOAD_DIR (default ``instance/uploads``, outside the code and
ignored by git) and are served by the app at ``/media/<key>``.
"""

import io
import logging
import mimetypes
import os
import uuid
from datetime import UTC, datetime

from flask import current_app, send_from_directory, url_for
from PIL import Image, ImageOps, UnidentifiedImageError

log = logging.getLogger(__name__)

CACHE_FOREVER = "public, max-age=31536000, immutable"
MAX_IMAGE_SIDE = 2000  # px; larger uploads are scaled down
THUMB_SIZE = (400, 400)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


class InvalidImage(ValueError):
    """The upload isn't an image we accept (shown to the admin)."""


class LocalStorage:
    kind = "local"

    def __init__(self, root):
        self.root = os.path.abspath(root)

    def save(self, key, data, content_type):
        path = os.path.join(self.root, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)

    def exists(self, key):
        return os.path.exists(os.path.join(self.root, key))

    def url(self, key):
        return url_for("media", key=key)


class R2Storage:
    """Cloudflare R2 through its S3-compatible API."""

    kind = "r2"

    def __init__(self, account_id, access_key_id, secret_access_key, bucket, public_url, client=None):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.public_url = public_url.rstrip("/")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )

    def save(self, key, data, content_type):
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, CacheControl=CACHE_FOREVER
        )

    def exists(self, key):
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False

    def url(self, key):
        return f"{self.public_url}/{key}"


R2_SETTINGS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_URL")


def init_storage(app):
    config = app.config
    if all(config.get(name) for name in R2_SETTINGS):
        storage = R2Storage(*(config[name] for name in R2_SETTINGS))
        log.info("Image uploads go to R2 bucket %s", config["R2_BUCKET"])
    else:
        missing = [name for name in R2_SETTINGS if not config.get(name)]
        if len(missing) < len(R2_SETTINGS):
            log.warning(
                "R2 is partly configured (missing %s); using local uploads instead.", ", ".join(missing)
            )
        storage = LocalStorage(config.get("UPLOAD_DIR") or os.path.join(app.instance_path, "uploads"))
    app.extensions["storage"] = storage

    @app.route("/media/<path:key>")
    def media(key):
        if not isinstance(storage, LocalStorage):
            return "", 404
        return send_from_directory(storage.root, key, max_age=31536000)

    app.jinja_env.globals["image_url"] = image_url


def get_storage():
    return current_app.extensions["storage"]


def thumb_key(key):
    base, _ = os.path.splitext(key)
    return f"{base}_thumb.jpg"


def image_url(key, thumb=False):
    """Public URL for a stored image key; the placeholder when there's none."""
    if not key:
        return url_for("static", filename="images/default.jpg")
    return get_storage().url(thumb_key(key) if thumb else key)


def _encode(image, fmt):
    buf = io.BytesIO()
    if fmt == "JPEG":
        image.convert("RGB").save(buf, "JPEG", quality=88, optimize=True, progressive=True)
    else:
        image.save(buf, fmt, optimize=True)
    return buf.getvalue()


def save_image(file_storage, folder):
    """Validate, clean and store an uploaded image plus a thumbnail. Returns the new key.

    Photos are re-encoded, which strips camera metadata such as GPS location,
    applies the EXIF rotation, and scales very large images down.
    """
    try:
        image = Image.open(file_storage.stream)
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise InvalidImage("That file isn't an image we can read.") from error
    if image.format not in ALLOWED_FORMATS:
        raise InvalidImage("Please upload a JPEG, PNG, WebP or GIF image.")

    image = ImageOps.exif_transpose(image)
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    fmt, ext = ("PNG", "png") if has_alpha else ("JPEG", "jpg")

    now = datetime.now(UTC)
    key = f"{folder}/{now:%Y/%m}/{uuid.uuid4().hex}.{ext}"
    thumb = image.copy()
    thumb.thumbnail(THUMB_SIZE)
    if has_alpha:  # thumbnails are JPEG: put transparent images on white
        background = Image.new("RGB", thumb.size, "white")
        background.paste(thumb, mask=thumb.convert("RGBA").split()[-1])
        thumb = background

    storage = get_storage()
    storage.save(key, _encode(image, fmt), mimetypes.types_map[f".{ext}"])
    storage.save(thumb_key(key), _encode(thumb, "JPEG"), "image/jpeg")
    log.info("Stored image %s (%s)", key, storage.kind)
    return key
