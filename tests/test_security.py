"""Security behaviour: secrets, admin access, CSRF, redirects, stored payment data."""

import re

import pytest

from app import create_app
from app.extension import db
from app.models import Payment, User
from app.seed import seed_admin
from app.urls import is_safe_next
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, ONE_SIZE

CSRF_EXPIRED = "That form had expired"


def assert_csrf_rejected(client, resp):
    """A request without a valid CSRF token is bounced back with a message, and not processed."""
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        messages = [m for _, m in sess.get("_flashes", [])]
    assert any(CSRF_EXPIRED in m for m in messages), messages


def login(client, email, password, next_url=None):
    url = "/auth/login" + (f"?next={next_url}" if next_url else "")
    return client.post(url, data={"email": email, "password": password})


def test_app_refuses_to_start_without_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"SECRET_KEY": None})


def test_admin_comes_from_environment_not_a_default(app):
    with app.app_context():
        assert User.query.filter_by(email="user@admin.com").first() is None
        admin = User.query.filter_by(email=ADMIN_EMAIL).one()
        assert admin.check_password(ADMIN_PASSWORD)
        assert not admin.check_password("admin")
        assert [r.name for r in admin.roles] == ["admin"]


def test_no_admin_is_seeded_without_credentials(app):
    with app.app_context():
        before = User.query.count()
        app.config.update(ADMIN_EMAIL="someone@example.com", ADMIN_PASSWORD=None)
        try:
            seed_admin()
        finally:
            app.config.update(ADMIN_EMAIL=ADMIN_EMAIL, ADMIN_PASSWORD=ADMIN_PASSWORD)
        assert User.query.count() == before


def test_changing_admin_password_in_env_resets_it(app):
    with app.app_context():
        app.config["ADMIN_PASSWORD"] = "a-new-long-password"
        try:
            seed_admin()
            assert User.query.filter_by(email=ADMIN_EMAIL).one().check_password("a-new-long-password")
        finally:
            app.config["ADMIN_PASSWORD"] = ADMIN_PASSWORD
            seed_admin()


def test_admin_requires_login(client):
    for url in ["/admin/", "/admin/product/", "/admin/user/"]:
        resp = client.get(url)
        assert resp.status_code == 302, url
        assert resp.headers["Location"].startswith("/admin/login?next=/admin/"), url


def test_admin_rejects_non_admin_users(app, client):
    with app.app_context():
        user = User(first_name="Shopper", last_name="One", email="shopper@example.com")
        user.set_password("shopper-password")
        db.session.add(user)
        db.session.commit()
    assert login(client, "shopper@example.com", "shopper-password").status_code == 302
    assert client.get("/customer/profile").status_code == 200  # logged in...
    assert client.get("/admin/product/").status_code == 302  # ...but not an admin


def test_admin_login_returns_to_admin(client):
    resp = login(client, ADMIN_EMAIL, ADMIN_PASSWORD, next_url="/admin/")
    assert resp.headers["Location"] == "/admin/"
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/product/").status_code == 200


@pytest.mark.parametrize(
    "target,safe",
    [
        ("/admin/", True),
        ("/catalog/collection?x=1", True),
        ("http://evil.example/", False),
        ("//evil.example/", False),
        ("/\\evil.example/", False),
        ("javascript:alert(1)", False),
        ("", False),
        (None, False),
    ],
)
def test_login_next_only_allows_local_paths(target, safe):
    assert is_safe_next(target) is safe


def test_post_without_csrf_token_is_rejected(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        assert_csrf_rejected(client, client.post("/checkout/remove/1"))
        assert_csrf_rejected(client, login(client, ADMIN_EMAIL, ADMIN_PASSWORD))
        assert client.get("/customer/profile").status_code == 302  # the login above did not happen

        page = client.get("/auth/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page).group(1)
        resp = client.post("/checkout/remove/1", data={"csrf_token": token})
        assert resp.status_code == 302
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


def test_payment_table_stores_no_card_data():
    columns = set(Payment.__table__.columns.keys())
    assert not columns & {"account_number", "account_name", "expiry_month", "expiry_year"}


def test_unknown_page_returns_404(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert b"Page not found" in resp.data


def test_debug_is_off_by_default(app):
    assert app.debug is False


def test_admin_can_save_with_csrf_on_and_is_protected_without_it(app, client):
    from app.models import Product

    app.config["WTF_CSRF_ENABLED"] = True
    try:
        page = client.get("/auth/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page).group(1)
        login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": token}
        assert client.post("/auth/login", data=login_data).status_code == 302

        page = client.get("/admin/product/new/").get_data(as_text=True)
        form = page[page.index("data-bz-editor") : page.index("</form>")]
        tokens = re.findall(r'name="csrf_token"[^>]*value="([^"]+)"', form)
        assert len(tokens) == 1  # exactly one token per form, or WTForms reads the wrong one
        data = {"name": "CSRF Ring", "price": "12", **ONE_SIZE}
        assert_csrf_rejected(client, client.post("/admin/product/new/", data=data))
        with app.app_context():
            assert Product.query.filter_by(name="CSRF Ring").count() == 0
        resp = client.post("/admin/product/new/", data={**data, "csrf_token": tokens[0]})
        assert resp.status_code == 302
        with app.app_context():
            product = Product.query.filter_by(name="CSRF Ring").one()
            assert product.sku == "BZ-CSRF-RING"  # made from the name
            assert [(o.name, o.stock) for o in product.options] == [("One Size", 5)]
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


def test_admin_can_put_a_product_in_categories(app, client):
    from app.models import Category, Product

    with app.app_context():
        rings = Category.query.filter_by(code="ACC-RINGS").one().id
        bracelets = Category.query.filter_by(code="ACC-BANGLES").one().id
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    page = client.get("/admin/product/new/").get_data(as_text=True)
    assert 'name="categories"' in page
    data = {
        "sku": "ADMIN-CAT-1",
        "name": "Category Ring",
        "compare_at_price": "10",
        "price": "9",
        "is_active": "y",
        "categories": [str(rings), str(bracelets)],
        **ONE_SIZE,
    }
    assert client.post("/admin/product/new/", data=data).status_code == 302
    with app.app_context():
        product = Product.query.filter_by(sku="ADMIN-CAT-1").one()
        assert sorted(c.code for c in product.categories) == ["ACC-BANGLES", "ACC-RINGS"]
