"""Shippo labels and tracking webhooks, with the Shippo API replaced by a fake."""

import pytest

from app.extension import db
from app.models import Order
from app.services import shippo
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import checkout
from tests.test_security import login

SHIP_FROM = {
    "name": "BazaarE' Studio",
    "company": "BazaarE'",
    "street1": "1 Craft Way",
    "street2": "",
    "city": "Edison",
    "state": "NJ",
    "zip": "08817",
    "country": "US",
    "phone": "5555550199",
    "email": "studio@example.com",
}


class FakeShippo:
    def __init__(self):
        self.calls = []
        self.transaction = {
            "object_id": "txn_1",
            "status": "SUCCESS",
            "tracking_number": "9400100000000000000001",
            "label_url": "https://shippo-delivery.example/label.pdf?Expires=1",
            "rate": {"provider": "USPS"},
            "messages": [],
        }

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == "/shipments/":
            return {
                "rates": [
                    {
                        "object_id": "rate_exp",
                        "provider": "UPS",
                        "servicelevel": {"name": "Next Day Air"},
                        "amount": "31.20",
                        "currency": "USD",
                        "estimated_days": 1,
                        "duration_terms": "Next business day",
                    },
                    {
                        "object_id": "rate_cheap",
                        "provider": "USPS",
                        "servicelevel": {"name": "Ground Advantage"},
                        "amount": "4.85",
                        "currency": "USD",
                        "estimated_days": 3,
                        "duration_terms": "2-5 days",
                    },
                ]
            }
        if path == "/transactions/":
            return self.transaction
        if path.startswith("/transactions/"):
            return {"label_url": "https://shippo-delivery.example/label.pdf?Expires=2"}
        raise AssertionError(path)


@pytest.fixture
def fake(app, monkeypatch):
    fake = FakeShippo()
    monkeypatch.setattr(shippo, "_request", fake)
    app.config.update(SHIPPO_API_KEY="shippo_test_abc", SHIP_FROM=SHIP_FROM)
    yield fake
    app.config.update(SHIPPO_API_KEY=None, SHIP_FROM={k: "" for k in SHIP_FROM})


def test_without_settings_the_order_page_says_what_is_missing(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get(f"/admin/order/details/?id={order_id}").get_data(as_text=True)
    assert "To buy labels here, add SHIPPO_API_KEY" in html
    assert "Enter the tracking number" in html  # manual tracking still works


def test_rates_then_buy_label_marks_the_order_shipped(app, client, product_ids, fake):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get(f"/admin/order/details/?id={order_id}").get_data(as_text=True)
    assert "Get shipping rates" in html
    html = client.get(f"/admin/order/details/?id={order_id}&rates=1").get_data(as_text=True)
    assert html.index("Ground Advantage") < html.index("Next Day Air")  # cheapest first
    assert "Buy $4.85" in html and "test mode" in html
    _, path, shipment = fake.calls[0]
    assert shipment["address_from"]["zip"] == "08817" and shipment["address_to"]["city"] == "Albany"
    assert shipment["parcels"][0] == {
        "length": "9",
        "width": "6",
        "height": "1",
        "distance_unit": "in",
        "weight": "4",
        "mass_unit": "oz",
    }

    resp = client.post(f"/admin/order/label/{order_id}", data={"rate_id": "rate_cheap"})
    assert resp.status_code == 302
    assert fake.calls[-1][2]["rate"] == "rate_cheap" and fake.calls[-1][2]["label_file_type"] == "PDF"
    with app.app_context():
        order = db.session.get(Order, order_id)
        assert (order.status, order.carrier, order.tracking_number) == (
            "SHIPPED",
            "USPS",
            "9400100000000000000001",
        )
        assert order.shippo_transaction_id == "txn_1" and order.shipped_at
    html = client.get(f"/admin/order/details/?id={order_id}").get_data(as_text=True)
    assert "Print shipping label" in html and "Label bought" in html
    printed = client.get(f"/admin/order/label/{order_id}/print")
    assert printed.headers["Location"].endswith("Expires=2")  # always a fresh link


def test_a_refused_label_keeps_the_order_placed(app, client, product_ids, fake):
    fake.transaction = {"status": "ERROR", "messages": [{"text": "Address not deliverable"}]}
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    client.post(f"/admin/order/label/{order_id}", data={"rate_id": "rate_cheap"})
    with app.app_context():
        assert db.session.get(Order, order_id).status == "PLACED"
    assert "Address not deliverable" in client.get(f"/admin/order/details/?id={order_id}").get_data(
        as_text=True
    )


def _set_tracking(app, order_id, number):
    with app.app_context():
        order = db.session.get(Order, order_id)
        order.status, order.carrier, order.tracking_number = "SHIPPED", "USPS", number
        db.session.commit()


def test_tracking_webhook_marks_orders_delivered(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    _set_tracking(app, order_id, "TRACK-DELIVER-1")
    payload = {
        "event": "track_updated",
        "test": True,
        "data": {
            "tracking_number": "TRACK-DELIVER-1",
            "carrier": "usps",
            "tracking_status": {"status": "DELIVERED"},
        },
    }
    resp = client.post("/webhooks/shippo?token=hook-secret", json=payload)
    assert resp.status_code == 200 and resp.get_json()["order"] == f"BZ-{order_id:06d}"
    with app.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == "DELIVERED" and order.delivered_at is not None


def test_tracking_webhook_needs_the_secret(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    _set_tracking(app, order_id, "TRACK-SECRET-1")
    payload = {
        "event": "track_updated",
        "data": {"tracking_number": "TRACK-SECRET-1", "tracking_status": {"status": "DELIVERED"}},
    }
    assert client.post("/webhooks/shippo", json=payload).status_code == 403
    assert client.post("/webhooks/shippo?token=wrong", json=payload).status_code == 403
    with app.app_context():
        assert db.session.get(Order, order_id).status == "SHIPPED"


def test_unknown_tracking_numbers_and_other_events_are_ignored(client):
    payload = {
        "event": "track_updated",
        "data": {"tracking_number": "NOPE", "tracking_status": {"status": "DELIVERED"}},
    }
    assert client.post("/webhooks/shippo?token=hook-secret", json=payload).get_json() == {
        "ok": True,
        "order": None,
    }
    assert (
        client.post("/webhooks/shippo?token=hook-secret", json={"event": "batch_created"}).status_code == 200
    )
