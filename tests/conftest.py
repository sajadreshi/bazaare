import os

import pytest

from app import create_app, db
from app.seed import seed_all

# Set TEST_DATABASE_URL to run against Postgres, e.g.
#   TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bazaare_test
# The tests drop and recreate every table in that database.
TEST_DB = os.environ.get("TEST_DATABASE_URL", "sqlite://")
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(scope="session")
def app():
    # Flask-Admin views are registered on a module-level Admin, so build the app once.
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": TEST_DB,
            "WTF_CSRF_ENABLED": False,
            "ADMIN_EMAIL": ADMIN_EMAIL,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
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
