"""Cart and checkout services: behaviour added or tightened in the service-layer refactor."""

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
    assert 'class="bz-badge">1</span>' in client.get("/").get_data(as_text=True)


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
        hidden = Product(sku="HIDDEN-1", name="Hidden", compare_at_price=1, price=1, is_active=False)
        sizeless = Product(sku="NOSIZE-1", name="No Size", compare_at_price=1, price=1, is_active=True)
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


def test_shipping_method_must_be_one_we_offer(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        cart_id = add_to_cart(client, pid, small).id
    client.post(
        "/checkout/order",
        data={"form_id": "shipping_method_form", "shipping_method": "OVERNIGHT"},
        headers=REFERER,
    )
    with app.app_context():
        assert db.session.get(Cart, cart_id).shipping_method is None  # unknown method ignored
    client.post(
        "/checkout/order",
        data={"form_id": "shipping_method_form", "shipping_method": "EXPRESS"},
        headers=REFERER,
    )
    with app.app_context():
        cart = db.session.get(Cart, cart_id)
        assert cart.shipping_method == "EXPRESS" and cart.total_shipping == Decimal("14.99")


def test_standard_shipping_is_free_over_the_threshold(app):
    from app.services.shipping import METHODS

    standard = METHODS["STANDARD"]
    assert standard.charge(Decimal("49.99")) == Decimal("5.99")
    assert standard.charge(Decimal("50.00")) == Decimal("0.00")


def test_estimates_skip_weekends_and_holidays(app):
    import datetime as dt

    from app.models import Holiday
    from app.services.shipping import add_business_days

    with app.app_context():
        friday = dt.date(2026, 12, 4)
        assert add_business_days(friday, 1) == dt.date(2026, 12, 7)  # Monday
        db.session.add(Holiday(holiday_date=dt.datetime(2026, 12, 7)))
        db.session.commit()
        assert add_business_days(friday, 1) == dt.date(2026, 12, 8)  # Monday is a holiday


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
