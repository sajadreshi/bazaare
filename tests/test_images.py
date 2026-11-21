"""Image uploads: admin field, local storage fallback, and the R2 backend (with a stubbed S3 client)."""

import io
import os
import re

import pytest
from botocore.stub import Stubber
from PIL import Image

from app.extension import db
from app.models import Product
from app.storage import CACHE_FOREVER, LocalStorage, R2Storage, image_url, init_storage
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login

KEY_PATTERN = r"products/\d{4}/\d{2}/[0-9a-f]{32}\.(jpg|png)"


def image_file(size=(1200, 800), mode="RGB", fmt="JPEG", exif=None):
    buf = io.BytesIO()
    image = Image.new(mode, size, (200, 160, 80) if mode == "RGB" else (200, 160, 80, 120))
    image.save(buf, fmt, **({"exif": exif} if exif else {}))
    buf.seek(0)
    return buf


def upload_product(client, sku, file, filename="ring.jpg", **extra):
    data = {
        "sku": sku,
        "name": sku,
        "compare_at_price": "10",
        "price": "9",
        "is_active": "y",
        "main_image": (file, filename),
        **extra,
    }
    return client.post("/admin/product/new/", data=data, content_type="multipart/form-data")


@pytest.fixture
def admin_client(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return client


def stored_path(app, key):
    return os.path.join(app.config["UPLOAD_DIR"], key)


def test_admin_upload_goes_to_storage_with_a_unique_key(app, admin_client):
    assert upload_product(admin_client, "IMG-1", image_file()).status_code == 302
    assert upload_product(admin_client, "IMG-2", image_file()).status_code == 302  # same file name
    with app.app_context():
        keys = [Product.query.filter_by(sku=s).one().main_image for s in ("IMG-1", "IMG-2")]
    assert all(re.fullmatch(KEY_PATTERN, k) for k in keys) and keys[0] != keys[1]
    for key in keys:
        assert os.path.exists(stored_path(app, key))
        with Image.open(stored_path(app, key.replace(".jpg", "_thumb.jpg"))) as thumb:
            assert max(thumb.size) == 400

    resp = admin_client.get(f"/media/{keys[0]}")
    assert resp.status_code == 200 and resp.mimetype == "image/jpeg"
    assert "max-age=31536000" in resp.headers["Cache-Control"]

    with app.app_context():
        pid = Product.query.filter_by(sku="IMG-1").one().id
    page = admin_client.get(f"/catalog/product/{pid}").get_data(as_text=True)
    assert f"/media/{keys[0]}" in page


def test_photos_are_cleaned_scaled_and_stripped_of_location(app, admin_client):
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (51.0, 30.0, 0.0)}  # GPS info
    exif[0x010F] = "PhoneMaker"
    assert upload_product(admin_client, "IMG-BIG", image_file((5000, 3000), exif=exif)).status_code == 302
    with app.app_context():
        key = Product.query.filter_by(sku="IMG-BIG").one().main_image
    with Image.open(stored_path(app, key)) as stored:
        assert stored.size == (2000, 1200)
        assert not stored.getexif()


def test_transparent_png_stays_png(app, admin_client):
    file = image_file((300, 300), mode="RGBA", fmt="PNG")
    assert upload_product(admin_client, "IMG-PNG", file, filename="logo.png").status_code == 302
    with app.app_context():
        key = Product.query.filter_by(sku="IMG-PNG").one().main_image
    assert key.endswith(".png")
    with Image.open(stored_path(app, key)) as stored:
        assert stored.mode == "RGBA"


@pytest.mark.parametrize(
    "content,filename",
    [(b"not an image at all", "ring.jpg"), (b"%PDF-1.4 ...", "ring.pdf"), (b"<svg/>", "ring.svg")],
)
def test_non_images_are_rejected(app, admin_client, content, filename):
    resp = upload_product(admin_client, "IMG-BAD", io.BytesIO(content), filename=filename)
    assert resp.status_code == 200  # form shown again with an error
    assert "JPEG, PNG, WebP or GIF" in resp.get_data(as_text=True) or "isn&#39;t an image" in resp.get_data(
        as_text=True
    )
    with app.app_context():
        assert Product.query.filter_by(sku="IMG-BAD").count() == 0


def test_removing_an_image_keeps_the_file_for_past_orders(app, admin_client):
    upload_product(admin_client, "IMG-DEL", image_file())
    with app.app_context():
        product = Product.query.filter_by(sku="IMG-DEL").one()
        pid, key = product.id, product.main_image
    data = {
        "sku": "IMG-DEL",
        "name": "IMG-DEL",
        "compare_at_price": "10",
        "price": "9",
        "_main_image-delete": "y",
    }
    assert admin_client.post(f"/admin/product/edit/?id={pid}", data=data).status_code == 302
    with app.app_context():
        assert db.session.get(Product, pid).main_image is None
    assert os.path.exists(stored_path(app, key))


def test_placeholder_when_there_is_no_image(app):
    with app.test_request_context():
        assert image_url(None) == "/static/images/default.jpg"
        assert image_url("products/2026/11/abc.jpg", thumb=True) == "/media/products/2026/11/abc_thumb.jpg"


def test_r2_storage_uploads_with_long_cache_and_public_url():
    storage = R2Storage("acct", "key-id", "secret", "bazaare-media", "https://media.example.com/")
    with Stubber(storage.client) as stub:
        stub.add_response(
            "put_object",
            {},
            {
                "Bucket": "bazaare-media",
                "Key": "products/2026/11/abc.jpg",
                "Body": b"jpeg-bytes",
                "ContentType": "image/jpeg",
                "CacheControl": CACHE_FOREVER,
            },
        )
        storage.save("products/2026/11/abc.jpg", b"jpeg-bytes", "image/jpeg")
        stub.assert_no_pending_responses()
    assert storage.client.meta.endpoint_url == "https://acct.r2.cloudflarestorage.com"
    assert storage.url("products/2026/11/abc.jpg") == "https://media.example.com/products/2026/11/abc.jpg"


def bare_app(**config):
    from flask import Flask

    app = Flask("storage-test")
    app.config.update(config)
    return app


def test_r2_is_used_only_when_fully_configured(tmp_path):
    full = {
        "R2_ACCOUNT_ID": "acct",
        "R2_ACCESS_KEY_ID": "id",
        "R2_SECRET_ACCESS_KEY": "secret",
        "R2_BUCKET": "bucket",
        "R2_PUBLIC_URL": "https://pub-x.r2.dev",
    }
    app = bare_app(**full)
    init_storage(app)
    assert isinstance(app.extensions["storage"], R2Storage)

    app = bare_app(**{**full, "R2_SECRET_ACCESS_KEY": None}, UPLOAD_DIR=str(tmp_path))
    init_storage(app)
    assert isinstance(app.extensions["storage"], LocalStorage)
    with app.test_request_context():
        assert app.extensions["storage"].url("a/b.jpg") == "/media/a/b.jpg"


def test_the_test_suite_never_uses_a_real_bucket(app):
    # .env on a developer machine may hold real R2 keys; tests must still write locally.
    assert isinstance(app.extensions["storage"], LocalStorage)
