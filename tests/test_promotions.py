"""Promotions: coupon codes at checkout, usage rules, the free-shipping amount and the coupon box switch."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.extension import db
from app.models import Coupon, Order, ShopSettings, utcnow
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import REFERER, add_to_cart, address
from tests.test_security import login


@pytest.fixture(autouse=True)
def clean(app):
    yield
    with app.app_context():
        db.session.query(Order).update({Order.coupon_code: None})
        from app.models import Cart

        db.session.query(Cart).update({Cart.coupon_id: None})
        db.session.query(Coupon).delete()
        row = db.session.query(ShopSettings).first()
        if row is not None:
            row.free_shipping_over, row.coupons_enabled = Decimal("50"), True
        db.session.commit()


def coupon(app, **fields):
    with app.app_context():
        db.session.add(Coupon(**{"kind": "PERCENT", "value": Decimal("10"), **fields}))
        db.session.commit()


def bag(app, client, product_ids):
    pid, small, _ = product_ids  # one Gold Signet at $99.99
    with app.app_context():
        add_to_cart(client, pid, small)
    client.post("/checkout/order", data=address("shipping_form"), headers=REFERER)


def apply(client, code):
    client.post("/checkout/order", data={"form_id": "coupon_apply", "code": code})
    with client.session_transaction() as sess:
        return [m for _, m in sess.pop("_flashes", [])]


def place(client):
    return client.post("/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"})


def last_order(app):
    with app.app_context():
        order = Order.query.order_by(Order.id.desc()).first()
        return (
            order.total_merchandise,
            order.total_discount,
            order.total_shipping,
            order.total,
            order.coupon_code,
        )


def test_percent_coupon_is_applied_at_checkout_and_counted(app, client, product_ids):
    coupon(app, code="DIWALI15", value=Decimal("15"))
    bag(app, client, product_ids)
    assert apply(client, " diwali15 ") == ["DIWALI15 applied: 15% off."]
    html = client.get("/checkout/order").get_data(as_text=True)
    assert "Discount (DIWALI15)" in html and "−$15.00" in html
    assert "/checkout/confirm/" in place(client).headers["Location"]
    # 99.99 - 15.00 = 84.99 (still over $50: shipping free)
    assert last_order(app) == (
        Decimal("99.99"),
        Decimal("15.00"),
        Decimal("0.00"),
        Decimal("84.99"),
        "DIWALI15",
    )
    with app.app_context():
        assert Coupon.query.filter_by(code="DIWALI15").one().times_used == 1


def test_dollar_coupon_and_free_shipping_judged_after_the_discount(app, client, product_ids):
    coupon(app, code="TAKE60", kind="AMOUNT", value=Decimal("60"))
    bag(app, client, product_ids)
    apply(client, "TAKE60")
    place(client)
    # 99.99 - 60 = 39.99: under $50 after the discount, so Standard shipping is charged.
    assert last_order(app) == (
        Decimal("99.99"),
        Decimal("60.00"),
        Decimal("5.99"),
        Decimal("45.98"),
        "TAKE60",
    )


@pytest.mark.parametrize(
    "fields,message",
    [
        ({"is_active": False}, "isn't valid"),
        ({"ends_at": utcnow() - timedelta(days=1)}, "has expired"),
        ({"starts_at": utcnow() + timedelta(days=3)}, "starts on"),
        ({"max_uses": 1, "times_used": 1}, "fully used"),
        ({"min_order": Decimal("150")}, "needs a bag of $150.00 or more"),
    ],
)
def test_coupons_that_cannot_be_used_explain_why(app, client, product_ids, fields, message):
    coupon(app, code="NOPE", **fields)
    bag(app, client, product_ids)
    assert any(message in m for m in apply(client, "NOPE"))
    assert any("isn't valid" in m for m in apply(client, "WHATEVER"))
    place(client)
    assert last_order(app)[1] == Decimal("0.00")


def test_a_coupon_that_runs_out_before_the_order_is_refused_at_placing(app, client, product_ids):
    coupon(app, code="LAST1", max_uses=1)
    bag(app, client, product_ids)
    apply(client, "LAST1")
    with app.app_context():
        Coupon.query.filter_by(code="LAST1").one().times_used = 1
        db.session.commit()
    resp = place(client)
    assert resp.headers["Location"].endswith("/checkout/order")
    with client.session_transaction() as sess:
        assert any("fully used" in m for _, m in sess.get("_flashes", []))
    client.post("/checkout/order", data={"form_id": "coupon_remove"})
    assert "/checkout/confirm/" in place(client).headers["Location"]


def test_free_shipping_amount_is_a_setting(app, client, product_ids):
    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    resp = admin.post("/admin/promotions/", data={"free_shipping_over": "150", "coupons_enabled": "y"})
    assert resp.status_code == 302
    bag(app, client, product_ids)
    html = client.get("/checkout/shopcart").get_data(as_text=True)
    assert "away from free standard shipping" in html and "$50.01" in html  # 150 - 99.99
    place(client)
    assert last_order(app)[2] == Decimal("5.99")
    admin.post("/admin/promotions/", data={"free_shipping_over": "", "coupons_enabled": "y"})
    with app.app_context():
        assert db.session.query(ShopSettings).first().free_shipping_over is None


def test_switching_off_the_coupon_box_hides_it(app, client, product_ids):
    coupon(app, code="HIDDEN10")
    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    admin.post("/admin/promotions/", data={"free_shipping_over": "50"})  # box unticked
    bag(app, client, product_ids)
    assert "Have a coupon code?" not in client.get("/checkout/order").get_data(as_text=True)
    apply(client, "HIDDEN10")
    place(client)
    assert last_order(app)[1] == Decimal("0.00")


def test_admin_creates_coupons_with_tidy_codes_and_sensible_values(app):
    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    form = {"code": "spring sale!", "kind": "PERCENT", "value": "20", "is_active": "y"}
    assert admin.post("/admin/coupon/new/", data=form).status_code == 302
    with app.app_context():
        assert Coupon.query.filter_by(code="SPRINGSALE").one().offer == "20% off"
    html = admin.post("/admin/coupon/new/", data={**form, "code": "SPRINGSALE"}).get_data(as_text=True)
    assert "Already exists" in html or "already a coupon called SPRINGSALE" in html
    html = admin.post("/admin/coupon/new/", data={**form, "code": "TOOMUCH", "value": "150"}).get_data(
        as_text=True
    )
    assert "can&#39;t be more than 100" in html
    listing = admin.get("/admin/coupon/").get_data(as_text=True)
    assert "SPRINGSALE" in listing and "20% off" in listing and "Live" in listing
