"""Cart and checkout services: behaviour added or tightened in the service-layer refactor."""

import datetime
from decimal import Decimal

from app.extension import db
from app.models import Cart, Item, Product, User, Variant
from tests.test_checkout_flow import REFERER, add_to_cart, address
from tests.test_security import login


def test_guest_cart_is_kept_when_logging_in(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        user = User(first_name="Gia", last_name="Guest", email="gia@example.com")
        user.set_password("gia-password-1")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        guest_cart = add_to_cart(client, pid, small)
        guest_item = Item.query.filter_by(cart_id=guest_cart.id).one().id

    assert login(client, "gia@example.com", "gia-password-1").status_code == 302
    with app.app_context():
        cart = Cart.query.filter_by(customer_id=user_id, status="PENDING").one()
        assert [i.id for i in cart.pending_items] == [guest_item]
        assert cart.total_cart == Decimal("99.99")
    assert 'badge-warning">1</span>' in client.get("/").get_data(as_text=True)


def test_guest_items_merge_into_existing_user_cart(app, client, product_ids):
    pid, small, large = product_ids
    with app.app_context():
        user = User(first_name="Max", last_name="Merge", email="max@example.com")
        user.set_password("max-password-1")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    # Max adds a ring while signed in, signs out, adds another as a guest, signs back in.
    login(client, "max@example.com", "max-password-1")
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": small})
    client.get("/auth/logout")
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": large})
    login(client, "max@example.com", "max-password-1")
    with app.app_context():
        cart = Cart.query.filter_by(customer_id=user_id, status="PENDING").one()
        assert sorted(i.variant.size for i in cart.pending_items) == ["Ring size 6", "Ring size 9"]
        assert cart.total_cart == Decimal("209.98")


def test_inactive_or_sizeless_products_cannot_be_added(app, client):
    with app.app_context():
        hidden = Product(sku="HIDDEN-1", name="Hidden", retail_price=1, sale_price=1, is_active=False)
        sizeless = Product(sku="NOSIZE-1", name="No Size", retail_price=1, sale_price=1, is_active=True)
        db.session.add_all([hidden, sizeless])
        db.session.commit()
        hidden_id, sizeless_id = hidden.id, sizeless.id
    for pid, message in [(hidden_id, "not available"), (sizeless_id, "out of stock")]:
        resp = client.post(f"/catalog/product/{pid}", data={"pid": pid})
        assert resp.status_code == 302
        with client.session_transaction() as sess:
            flashes = [m for _, m in sess.pop("_flashes", [])]
        assert any(message in m for m in flashes), flashes
    with app.app_context():
        assert Item.query.filter(Item.product_id.in_([hidden_id, sizeless_id])).count() == 0


def test_delivery_date_must_be_one_we_offer(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        cart_id = add_to_cart(client, pid, small).id
    too_soon = datetime.date.today().isoformat()
    for date, window in [(too_soon, "Morning"), ("not-a-date", "Morning"), (None, "Midnight")]:
        date = date or (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        client.post(
            "/checkout/order",
            data={"form_id": "delivery_form", "delivery_date": date, "delivery_window": window},
            headers=REFERER,
        )
        with app.app_context():
            assert db.session.get(Cart, cart_id).delivery_date is None, (date, window)


def test_checkout_page_prefills_saved_address(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    client.post("/checkout/order", data=address("shipping_form"), headers=REFERER)
    html = client.get("/checkout/order").get_data(as_text=True)
    assert 'value="Lovelace"' in html
    assert "1 Main St" in html


def test_size_endpoint_lists_product_variants(app, client, product_ids):
    pid, small, large = product_ids
    data = client.get(f"/checkout/size/{pid}").get_json()
    assert [row[:2] for row in data] == [[small, "Ring size 6"], [large, "Ring size 9"]]
    assert client.get("/checkout/size/999999").get_json() == []


def test_cart_page_renders_items_and_totals(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
        variant = db.session.get(Variant, small)
        assert variant.size == "Ring size 6"
    html = client.get("/checkout/shopcart").get_data(as_text=True)
    assert "Gold Signet" in html and "Ring size 6" in html and "$99.99" in html
