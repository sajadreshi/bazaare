"""Account pages: profile, password change and saved addresses."""

import pytest

from app.extension import db
from app.models import User
from tests.test_checkout_flow import address
from tests.test_security import login


@pytest.fixture
def member(app, client):
    with app.app_context():
        user = User.query.filter_by(email="member@example.com").first()
        if user is None:
            user = User(first_name="Mem", last_name="Ber", email="member@example.com")
            db.session.add(user)
        user.set_password("member-password-1")
        db.session.commit()
    assert login(client, "member@example.com", "member-password-1").status_code == 302
    return "member@example.com"


def test_profile_update(app, client, member):
    resp = client.post(
        "/customer/profile",
        data={"first_name": "Meera", "last_name": "Bern", "cell_number": "5551234", "marketing_email": "y"},
    )
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email=member).one()
        assert (user.first_name, user.last_name, user.marketing_email, user.marketing_sms) == (
            "Meera",
            "Bern",
            True,
            False,
        )


def test_invalid_profile_keeps_what_was_typed(client, member):
    html = client.post("/customer/profile", data={"first_name": "", "last_name": "Typed"}).get_data(
        as_text=True
    )
    assert 'value="Typed"' in html


def test_password_change_requires_current_password(app, client, member):
    data = {
        "current_password": "wrong-password",
        "password": "brand-new-pass",
        "confirm_password": "brand-new-pass",
    }
    html = client.post("/customer/security", data=data).get_data(as_text=True)
    assert "isn&#39;t your current password" in html
    with app.app_context():
        assert User.query.filter_by(email=member).one().check_password("member-password-1")

    data["current_password"] = "member-password-1"
    assert client.post("/customer/security", data=data).status_code == 302
    with app.app_context():
        assert User.query.filter_by(email=member).one().check_password("brand-new-pass")


def test_new_password_must_be_long_enough(client, member):
    data = {"current_password": "member-password-1", "password": "short", "confirm_password": "short"}
    assert "at least 8 characters" in client.post("/customer/security", data=data).get_data(as_text=True)


def test_registration_rejects_short_passwords(client):
    data = {"first_name": "A", "last_name": "B", "email": "short@example.com", "password": "1234567"}
    assert "at least 8 characters" in client.post("/auth/register", data=data).get_data(as_text=True)


def test_saved_addresses(app, client, member):
    assert client.post("/customer/shipping", data=address("shipping_form")).status_code == 302
    html = client.get("/customer/shipping").get_data(as_text=True)
    assert "1 Main St" in html and "Albany" in html
    # The first shipping address also became the billing address.
    assert "Lovelace" in client.get("/customer/billing").get_data(as_text=True)

    billing = {**address("billing_form"), "address1": "9 Billing Rd"}
    assert client.post("/customer/billing", data=billing).status_code == 302
    assert "9 Billing Rd" in client.get("/customer/billing").get_data(as_text=True)
    assert "1 Main St" in client.get("/customer/shipping").get_data(as_text=True)


def test_register_signs_you_in_and_keeps_the_bag(app, client, product_ids):
    from tests.test_cart_service import add_to_cart

    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    data = {
        "first_name": "Nila",
        "last_name": "Rao",
        "email": "nila@example.com",
        "password": "a-long-password",
    }
    resp = client.post("/auth/register?next=/checkout/order", data=data)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/checkout/order")
    html = client.get("/customer/profile").get_data(as_text=True)
    assert "Hello, Nila" in html and "nila@example.com" in html
    assert "Gold Signet" in client.get("/checkout/shopcart").get_data(as_text=True)
    resp = client.post("/auth/register", data={**data, "first_name": "Again"})
    assert resp.status_code == 302  # already signed in: sent home
    client.get("/auth/logout")
    html = client.post("/auth/register", data=data).get_data(as_text=True)
    assert "already an account with this email" in html


def test_wrong_password_keeps_where_you_were_going(client, member):
    client.get("/auth/logout")
    resp = client.post("/auth/login?next=/customer/orders", data={"email": member, "password": "nope-nope"})
    html = resp.get_data(as_text=True)
    assert resp.status_code == 401 and "don&#39;t match an account" in html
    assert f'value="{member}"' in html and "nope-nope" not in html  # email kept, password not
    # The form still posts to the same address, so ?next survives the retry.
    resp = client.post(
        "/auth/login?next=/customer/orders", data={"email": member, "password": "member-password-1"}
    )
    assert resp.headers["Location"].endswith("/customer/orders")


def test_account_pages_share_the_new_layout(client, member):
    for url, heading in [
        ("/customer/profile", "Your details"),
        ("/customer/orders", "No orders yet"),
        ("/customer/shipping", "Shipping address"),
        ("/customer/security", "Change your password"),
    ]:
        html = client.get(url).get_data(as_text=True)
        assert 'class="bz-account__nav"' in html and heading in html, url
    client.post("/customer/shipping", data=address("shipping_form"))
    html = client.get("/customer/shipping").get_data(as_text=True)
    assert "1 Main St" in html and 'name="address1"' not in html  # saved: shown, not a form
    assert 'name="address1"' in client.get("/customer/shipping?edit=1").get_data(as_text=True)
    assert "Billing address" in client.get("/customer/billing").get_data(as_text=True)


def test_first_checkout_starts_from_the_account_details(app, client, product_ids):
    from tests.test_cart_service import add_to_cart

    with app.app_context():
        user = User(first_name="Ira", last_name="Sen", email="ira@example.com", cell_number="5550001111")
        user.set_password("ira-password-1")
        db.session.add(user)
        db.session.commit()
    login(client, "ira@example.com", "ira-password-1")
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    html = client.get("/checkout/order").get_data(as_text=True)
    assert 'value="Ira"' in html and 'value="ira@example.com"' in html and 'value="5550001111"' in html
