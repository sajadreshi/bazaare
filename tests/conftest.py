import pytest

from app import create_app, db
from app.seed import seed_all


@pytest.fixture(scope="session")
def app():
    # Flask-Admin views are registered on a module-level Admin, so build the app once.
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        seed_all()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
