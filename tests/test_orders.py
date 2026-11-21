"""Orders: snapshots, customer order history, admin status updates."""

from decimal import Decimal

from app.extension import db
from app.models import Order, Product, User
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import checkout
from tests.test_security import login


def test_order_keeps_its_prices_when_the_catalog_changes(app, client, product_ids):
    _, order_id = checkout(app, client, product_ids)
    with app.app_context():
        product = Product.query.filter_by(sku="FLOW-RING").one()
        product.sale_price = Decimal("150.00")
        product.name = "Renamed Ring"
        db.session.commit()
        line = db.session.get(Order, order_id).items[0]
        assert (line.name, line.price) == ("Gold Signet", Decimal("99.99"))
        product.sale_price = Decimal("99.99")
        product.name = "Gold Signet"
        db.session.commit()


def test_registered_customer_sees_only_their_orders(app, client, product_ids):
    with app.app_context():
        user = User(first_name="Rhea", last_name="Buyer", email="rhea@example.com")
        user.set_password("rhea-password-1")
        db.session.add(user)
        db.session.commit()
    assert login(client, "rhea@example.com", "rhea-password-1").status_code == 302
    _, order_id = checkout(app, client, product_ids)

    page = client.get("/customer/orders").get_data(as_text=True)
    assert f"BZ-{order_id:06d}" in page
    assert client.get(f"/customer/orderDetails/{order_id}").status_code == 200

    # A guest's order is not visible to Rhea.
    guest = app.test_client()
    _, guest_order = checkout(app, guest, product_ids)
    assert f"BZ-{guest_order:06d}" not in client.get("/customer/orders").get_data(as_text=True)
    assert client.get(f"/customer/orderDetails/{guest_order}").status_code == 404


def test_admin_can_update_order_status_but_not_create_orders(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert client.get("/admin/order/").status_code == 200
    assert client.get("/admin/order/new/").status_code == 302  # can_create = False
    resp = client.post(f"/admin/order/edit/?id={order_id}", data={"status": "SHIPPED"})
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Order, order_id).status == "SHIPPED"
