"""The admin's own sign-in page."""

import re

from app.extension import db
from app.models import User
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login  # noqa: F401

FAILED = "doesn&#39;t have admin access"


def admin_login(client, email, password, next_url=None):
    url = "/admin/login" + (f"?next={next_url}" if next_url else "")
    return client.post(url, data={"email": email, "password": password})


def test_admin_pages_send_visitors_to_the_admin_login(client):
    resp = client.get("/admin/order/")
    assert resp.headers["Location"] == "/admin/login?next=/admin/order/"
    page = client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "Sign in to manage the shop" in page
    assert "bazaare-logo.jpg" in page


def test_admin_signs_in_and_returns_to_the_page_they_wanted(client):
    resp = admin_login(client, ADMIN_EMAIL, ADMIN_PASSWORD, next_url="/admin/order/")
    assert resp.status_code == 302 and resp.headers["Location"] == "/admin/order/"
    assert client.get("/admin/order/").status_code == 200
    # Already signed in: the login page goes straight to the dashboard.
    assert client.get("/admin/login").headers["Location"] == "/admin/"


def test_admin_email_is_case_insensitive(client):
    assert admin_login(client, ADMIN_EMAIL.upper(), ADMIN_PASSWORD).status_code == 302


def test_next_cannot_leave_the_admin(client):
    for target in ["//evil.example/", "http://evil.example/", "/checkout/shopcart"]:
        resp = admin_login(client, ADMIN_EMAIL, ADMIN_PASSWORD, next_url=target)
        assert resp.headers["Location"] == "/admin/", target
        client.get("/admin/logout")


def test_wrong_password_and_shoppers_get_the_same_refusal(app, client):
    with app.app_context():
        if not User.query.filter_by(email="shop-only@example.com").first():
            user = User(first_name="Shop", last_name="Only", email="shop-only@example.com")
            user.set_password("shopper-password")
            db.session.add(user)
            db.session.commit()
    for email, password in [
        (ADMIN_EMAIL, "wrong-password"),
        ("nobody@example.com", "whatever-password"),
        ("shop-only@example.com", "shopper-password"),  # right password, but not an admin
    ]:
        resp = admin_login(client, email, password)
        assert resp.status_code == 401, email
        assert FAILED in resp.get_data(as_text=True)
        assert client.get("/admin/").status_code == 302  # still not in
    # The shopper can still use the shop's own login.
    assert login(client, "shop-only@example.com", "shopper-password").status_code == 302
    assert "isn't an admin account" in client.get("/admin/login").get_data(as_text=True)


def test_sign_out(client):
    admin_login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    page = client.get("/admin/").get_data(as_text=True)
    assert 'href="/admin/logout"' in page and "View shop" in page
    resp = client.get("/admin/logout")
    assert resp.headers["Location"] == "/admin/login"
    assert client.get("/admin/").status_code == 302
    assert "You have been signed out." in client.get("/admin/login").get_data(as_text=True)


def test_admin_login_needs_csrf_token(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        # A stale sign-in page bounces back to itself with a message instead of "Bad Request".
        resp = client.post(
            "/admin/login",
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": "stale"},
            headers={"Referer": "http://localhost/admin/login"},
        )
        assert resp.headers["Location"] == "http://localhost/admin/login"
        assert "That form had expired" in client.get("/admin/login").get_data(as_text=True)
        assert client.get("/admin/").status_code == 302  # not signed in
        page = client.get("/admin/login").get_data(as_text=True)
        token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', page).group(1)
        resp = client.post(
            "/admin/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": token}
        )
        assert resp.status_code == 302
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


def test_csrf_tokens_do_not_expire_while_the_browser_session_lasts(app):
    # The admin sign-in page used to fail with "The CSRF token has expired" after an hour.
    assert app.config["WTF_CSRF_TIME_LIMIT"] is None
