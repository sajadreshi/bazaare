"""End-to-end guest checkout: add to cart, remove, addresses, delivery, place order."""

import datetime
from decimal import Decimal

import pytest

from app.extension import db
from app.models import Cart, Category, Item, Payment, Product, Variant

REFERER = {"Referer": "http://localhost/checkout/order"}


@pytest.fixture(scope="module")
def product_ids(app):
    with app.app_context():
        rings = Category.query.filter_by(code="RINGS").one()
        small = Variant(size="Ring size 6", quantity=1, is_default=True)
        large = Variant(size="Ring size 9", quantity=Decimal("1.10"))
        product = Product(
            sku="FLOW-RING",
            name="Gold Signet",
            retail_price=Decimal("120.00"),
            sale_price=Decimal("99.99"),
            material="18k gold",
            is_active=True,
            display=True,
        )
        product.categories.append(rings)
        small.products.append(product)
        large.products.append(product)
        db.session.add_all([product, small, large])
        db.session.commit()
        return product.id, small.id, large.id


def add_to_cart(client, pid, vid):
    resp = client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": vid})
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        customer_id = sess["customer_id"]
    cart = Cart.query.filter_by(customer_id=customer_id, status="PENDING").one()
    return cart


def address(form_id):
    return {
        "form_id": form_id,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "address1": "1 Main St",
        "city": "Albany",
        "state": "NY",
        "zip": "12207",
        "email": "ada@example.com",
        "phone": "5555550100",
    }


def test_add_and_remove_item(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        cart = add_to_cart(client, pid, small)
        item = Item.query.filter_by(cart_id=cart.id).one()
        assert item.product_price == Decimal("99.99")
        assert db.session.get(Cart, cart.id).total_cart == Decimal("99.99")
        item_id, cart_id = item.id, cart.id

    resp = client.post(f"/checkout/remove/{item_id}", headers=REFERER)
    assert resp.status_code == 302
    with app.app_context():
        assert Item.query.filter_by(cart_id=cart_id).count() == 0


def test_remove_rejects_get(client):
    # Deleting must not be triggerable from a plain link or <img>.
    assert client.get("/checkout/remove/1").status_code == 405


def test_remove_ignores_other_customers_items(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        cart = add_to_cart(client, pid, small)
        item_id = Item.query.filter_by(cart_id=cart.id).one().id
    other = app.test_client()
    other.get("/")  # give the other browser its own guest customer
    resp = other.post(f"/checkout/remove/{item_id}", headers=REFERER)
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Item, item_id) is not None


def test_change_size_reprices_item(app, client, product_ids):
    pid, small, large = product_ids
    with app.app_context():
        cart = add_to_cart(client, pid, small)
        item_id = Item.query.filter_by(cart_id=cart.id).one().id
    resp = client.post("/checkout/shopcart", data={"size": large, "productId": pid, "itemId": item_id})
    assert resp.status_code == 200
    with app.app_context():
        assert db.session.get(Item, item_id).product_price == Decimal("109.99")
        assert db.session.get(Cart, cart.id).total_cart == Decimal("109.99")


def test_place_order_requires_shipping_address(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    resp = client.post(
        "/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"}, headers=REFERER
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        messages = [m for _, m in sess.get("_flashes", [])]
    assert "Please complete your shipping address" in messages


def test_full_guest_checkout(app, client, product_ids):
    pid, small, _ = product_ids
    with app.app_context():
        cart_id = add_to_cart(client, pid, small).id

    assert client.post("/checkout/order", data=address("shipping_form"), headers=REFERER).status_code == 302
    assert client.post("/checkout/order", data=address("billing_form"), headers=REFERER).status_code == 302
    delivery = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    resp = client.post(
        "/checkout/order",
        data={"form_id": "delivery_form", "delivery_date": delivery, "delivery_window": "Morning"},
        headers=REFERER,
    )
    assert resp.status_code == 302

    resp = client.post(
        "/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"}, headers=REFERER
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/checkout/confirm/{cart_id}")

    with app.app_context():
        cart = db.session.get(Cart, cart_id)
        assert cart.status == "COMPLETED"
        assert {i.status for i in Item.query.filter_by(cart_id=cart_id)} == {"COMPLETED"}
        payment = Payment.query.filter_by(cart_id=cart_id).one()
        assert payment.transaction_status == "APPROVED"
        assert payment.approved_amount == Decimal("99.99")

    resp = client.get(f"/checkout/confirm/{cart_id}")
    assert resp.status_code == 200
    assert b"Gold Signet" in resp.data


@pytest.fixture(scope="module")
def cheap_product_ids(app):
    with app.app_context():
        variant = Variant(size="One size", quantity=1, is_default=True)
        product = Product(
            sku="FLOW-CHEAP",
            name="Plain Stud",
            retail_price=Decimal("2.00"),
            sale_price=Decimal("1.00"),
            is_active=True,
            display=True,
        )
        variant.products.append(product)
        db.session.add_all([product, variant])
        db.session.commit()
        return product.id, variant.id


def test_size_change_cannot_borrow_another_products_price(app, client, product_ids, cheap_product_ids):
    pid, small, large = product_ids
    cheap_pid, cheap_variant = cheap_product_ids
    with app.app_context():
        cart = add_to_cart(client, pid, small)
        item_id = Item.query.filter_by(cart_id=cart.id).one().id
    # The browser-supplied productId is ignored: price comes from the item's own product.
    client.post("/checkout/shopcart", data={"size": large, "productId": cheap_pid, "itemId": item_id})
    with app.app_context():
        assert db.session.get(Item, item_id).product_price == Decimal("109.99")
    # A size that belongs to a different product is refused.
    client.post("/checkout/shopcart", data={"size": cheap_variant, "productId": cheap_pid, "itemId": item_id})
    with app.app_context():
        item = db.session.get(Item, item_id)
        assert item.size_id == large
        assert item.product_price == Decimal("109.99")


def test_cannot_change_size_of_another_customers_item(app, client, product_ids):
    pid, small, large = product_ids
    with app.app_context():
        cart = add_to_cart(client, pid, small)
        item_id = Item.query.filter_by(cart_id=cart.id).one().id
    other = app.test_client()
    other.get("/")
    other.post("/checkout/shopcart", data={"size": large, "productId": pid, "itemId": item_id})
    with app.app_context():
        assert db.session.get(Item, item_id).size_id == small


def test_cart_badge_counts_items(app, client, product_ids):
    pid, small, large = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
        add_to_cart(client, pid, large)
    html = client.get("/").get_data(as_text=True)
    assert 'badge-warning">2</span>' in html


def test_cannot_view_another_customers_confirmation(app, client, product_ids):
    test_full_guest_checkout(app, client, product_ids)
    with app.app_context():
        cart_id = Cart.query.filter_by(status="COMPLETED").order_by(Cart.id.desc()).first().id
    assert client.get(f"/checkout/confirm/{cart_id}").status_code == 200
    other = app.test_client()
    other.get("/")
    assert other.get(f"/checkout/confirm/{cart_id}").status_code == 404


def test_order_cannot_be_placed_twice(app, client, product_ids):
    test_full_guest_checkout(app, client, product_ids)
    with app.app_context():
        cart_id = Cart.query.filter_by(status="COMPLETED").order_by(Cart.id.desc()).first().id
        payments = Payment.query.filter_by(cart_id=cart_id).count()
    client.post(
        "/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"}, headers=REFERER
    )
    with app.app_context():
        assert Payment.query.filter_by(cart_id=cart_id).count() == payments == 1


def test_earliest_offered_delivery_date_is_accepted(app, client, product_ids):
    from app.checkout.deliveryDateHelper import fetchDeliveryDays

    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
        earliest = fetchDeliveryDays()[0][0]
    for form in ("shipping_form", "billing_form"):
        client.post("/checkout/order", data=address(form), headers=REFERER)
    client.post(
        "/checkout/order",
        data={
            "form_id": "delivery_form",
            "delivery_date": earliest.isoformat(),
            "delivery_window": "Evening",
        },
        headers=REFERER,
    )
    resp = client.post(
        "/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"}, headers=REFERER
    )
    assert "/checkout/confirm/" in resp.headers["Location"]
