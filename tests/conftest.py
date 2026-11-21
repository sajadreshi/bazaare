import os
from decimal import Decimal

import pytest

from app import create_app, db
from app.models import Category, Product, Variant
from app.seed import seed_all

# Set TEST_DATABASE_URL to run against Postgres, e.g.
#   TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bazaare_test
# The tests drop and recreate every table in that database.
TEST_DB = os.environ.get("TEST_DATABASE_URL", "sqlite://")
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    # Flask-Admin views are registered on a module-level Admin, so build the app once.
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": TEST_DB,
            "WTF_CSRF_ENABLED": False,
            "ADMIN_EMAIL": ADMIN_EMAIL,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
            "UPLOAD_DIR": str(tmp_path_factory.mktemp("uploads")),
            # Never touch a real bucket from tests, even if .env has R2 keys.
            "R2_ACCOUNT_ID": None,
            "R2_ACCESS_KEY_ID": None,
            "R2_SECRET_ACCESS_KEY": None,
            "R2_BUCKET": None,
            "R2_PUBLIC_URL": None,
            # Never call the real Shippo API from tests.
            "SHIPPO_API_KEY": None,
            "SHIPPO_WEBHOOK_TOKEN": "hook-secret",
        }
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def product_ids(app):
    with app.app_context():
        rings = Category.query.filter_by(code="ACC-RINGS").one()
        small = Variant(size="Ring size 6", quantity=1, is_default=True)
        large = Variant(size="Ring size 9", quantity=Decimal("1.10"))
        product = Product(
            sku="FLOW-RING",
            name="Gold Signet",
            retail_price=Decimal("120.00"),
            sale_price=Decimal("99.99"),
            material="18k gold",
            is_active=True,
            display=True,
        )
        product.categories.append(rings)
        small.products.append(product)
        large.products.append(product)
        db.session.add_all([product, small, large])
        db.session.commit()
        return product.id, small.id, large.id
