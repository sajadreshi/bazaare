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
