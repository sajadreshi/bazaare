"""Order emails (confirmed, shipped, delivered, new-order alert) and the policy pages."""

import os

import pytest

from app import mailer
from app.extension import db, mail
from app.models import Order, Page, ShopSettings, User
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import checkout
from tests.test_security import login


@pytest.fixture
def admin(app):
    client = app.test_client()
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return client


@pytest.fixture(autouse=True)
def reset_settings(app):
    yield
    with app.app_context():
        row = db.session.query(ShopSettings).first()
        if row is not None:
            row.order_alert_email, row.support_email = None, "support@bazaare.com"
            db.session.commit()


def test_placing_an_order_emails_the_shopper_and_the_shop(app, client, product_ids):
    with mail.record_messages() as outbox:
        _, order_id = checkout(app, client, product_ids)
    by_to = {m.recipients[0]: m for m in outbox}
    assert set(by_to) == {"ada@example.com", ADMIN_EMAIL}
    number = f"BZ-{order_id:06d}"
    shopper = by_to["ada@example.com"]
    assert shopper.subject == f"Your BazaarE' order {number} is confirmed"
    assert "Thank you, Ada!" in shopper.html and "Gold Signet" in shopper.html and "$99.99" in shopper.html
    assert "Cash on delivery" in shopper.html and "/policies/returns" in shopper.html
    assert "Gold Signet" in shopper.body and "Total: $99.99" in shopper.body  # plain-text version
    shop = by_to[ADMIN_EMAIL]
    assert shop.subject.startswith(f"New order {number}: $99.99 from Ada Lovelace")
    assert f"/admin/order/details/?id={order_id}" in shop.html


def test_shipping_and_delivery_emails_follow_the_order_status(app, client, product_ids, admin):
    _, order_id = checkout(app, client, product_ids)
    with mail.record_messages() as outbox:
        admin.post(
            f"/admin/order/status/{order_id}",
            data={"status": "SHIPPED", "carrier": "USPS", "tracking_number": "9400111"},
        )
        admin.post(f"/admin/order/status/{order_id}", data={"status": "DELIVERED"})
        admin.post(f"/admin/order/status/{order_id}", data={"status": "DELIVERED"})  # no change: no email
    assert [m.subject.split(" is ")[-1].split(" was ")[-1] for m in outbox] == ["on its way", "delivered"]
    shipped, delivered = outbox
    assert "USPS" in shipped.html and "9400111" in shipped.html
    assert "tools.usps.com/go/TrackConfirmAction?tLabels=9400111" in shipped.html
    assert "Delivered. Enjoy!" in delivered.html and "Caring for your jewellery" in delivered.html


def test_hand_delivery_and_email_preferences(app, client, product_ids, admin):
    _, order_id = checkout(app, client, product_ids)
    with mail.record_messages() as outbox:
        admin.post(f"/admin/order/status/{order_id}", data={"status": "SHIPPED", "carrier": "Hand delivery"})
    assert "delivering your order to you by hand" in outbox[0].html

    # A registered shopper who turned off order-update emails still gets the confirmation only.
    with app.app_context():
        user = User(
            first_name="Quiet", last_name="Shopper", email="quiet@example.com", transactional_email=False
        )
        user.set_password("quiet-password-1")
        db.session.add(user)
        db.session.commit()
    shopper = app.test_client()
    login(shopper, "quiet@example.com", "quiet-password-1")
    with mail.record_messages() as outbox:
        _, quiet_order = checkout(app, shopper, product_ids)
        admin.post(
            f"/admin/order/status/{quiet_order}",
            data={"status": "SHIPPED", "carrier": "UPS", "tracking_number": "1Z9"},
        )
    assert [m.recipients[0] for m in outbox] == ["quiet@example.com", ADMIN_EMAIL]
    assert "/customer/orderDetails/" in outbox[0].html  # registered: link to their order


def test_email_settings_previews_and_test_send(app, client, product_ids, admin):
    _, order_id = checkout(app, client, product_ids)
    resp = admin.post(
        "/admin/emails/", data={"order_alert_email": "owner@example.com", "support_email": "help@example.com"}
    )
    assert resp.status_code == 302
    html = admin.get("/admin/emails/").get_data(as_text=True)
    assert "owner@example.com" in html and "No mail server yet" in html
    for kind in ("confirmed", "shipped", "delivered", "admin_new_order"):
        page = admin.get(f"/admin/emails/preview/{kind}/{order_id}")
        assert page.status_code == 200 and f"BZ-{order_id:06d}" in page.get_data(as_text=True), kind
    assert "help@example.com" in admin.get(f"/admin/emails/preview/confirmed/{order_id}").get_data(
        as_text=True
    )
    with mail.record_messages() as outbox:
        admin.post("/admin/emails/", data={"action": "test"})
    assert outbox[0].recipients == ["owner@example.com"] and outbox[0].subject.startswith("[Test]")


def test_without_a_mail_server_emails_are_saved_to_the_outbox(app, tmp_path, monkeypatch):
    monkeypatch.setattr(mailer, "uses_outbox", lambda a: True)
    monkeypatch.setattr(mailer, "outbox_dir", lambda a: str(tmp_path))
    with app.test_request_context():
        mailer.send("Hello there", ["someone@example.com"], "<p>Hi</p>", "Hi")
    files = sorted(os.listdir(tmp_path))
    assert [f.rsplit(".", 1)[1] for f in files] == ["eml", "html"]
    assert "someone@example.com" in (tmp_path / files[1]).read_text()


def test_policy_pages_are_published_linked_and_editable(app, client, admin):
    for slug, text in [
        ("shipping", "Where we ship"),
        ("returns", "14 days of delivery"),
        ("privacy", "We never sell your personal information"),
        ("terms", "State of New York"),
    ]:
        page = client.get(f"/policies/{slug}")
        assert page.status_code == 200 and text in page.get_data(as_text=True), slug
    footer = client.get("/").get_data(as_text=True)
    assert all(f"/policies/{s}" in footer for s in ("shipping", "returns", "privacy", "terms"))
    assert client.get("/policies/nope").status_code == 404

    with app.app_context():
        page_id = Page.query.filter_by(slug="returns").one().id
    form = {
        "title": "Returns & exchanges",
        "slug": "returns",
        "body": '<h2>30 days</h2><p>Now <a href="javascript:alert(1)">30</a> days.</p><script>x()</script>',
        "is_published": "y",
        "position": "20",
    }
    assert admin.post(f"/admin/page/edit/?id={page_id}", data=form).status_code == 302
    html = client.get("/policies/returns").get_data(as_text=True)
    assert "<h2>30 days</h2>" in html and "javascript:" not in html and "x()" not in html
    clash = admin.post(f"/admin/page/edit/?id={page_id}", data={**form, "slug": "terms"}).get_data(
        as_text=True
    )
    assert "already used by" in clash or "Already exists" in clash
    admin.post(f"/admin/page/edit/?id={page_id}", data={**form, "is_published": ""})
    assert client.get("/policies/returns").status_code == 404
    with app.app_context():
        Page.query.filter_by(slug="returns").one().is_published = True
        db.session.commit()


def test_orders_still_work_when_email_fails(app, client, product_ids, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("mail server down")

    monkeypatch.setattr(mailer, "send", broken)
    _, order_id = checkout(app, client, product_ids)
    with app.app_context():
        assert db.session.get(Order, order_id).status == "PLACED"
