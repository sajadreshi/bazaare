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


def test_admin_can_update_order_status_but_not_create_or_edit_orders(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert client.get("/admin/order/").status_code == 200
    assert client.get("/admin/order/new/").status_code == 302  # can_create = False
    assert client.get(f"/admin/order/edit/?id={order_id}").status_code == 302  # can_edit = False
    resp = client.post(f"/admin/order/status/{order_id}", data={"status": "SHIPPED"})
    assert resp.headers["Location"].startswith(f"/admin/order/details/?id={order_id}")
    with app.app_context():
        assert db.session.get(Order, order_id).status == "SHIPPED"
    client.post(f"/admin/order/status/{order_id}", data={"status": "LOST"})  # not a status: ignored
    with app.app_context():
        assert db.session.get(Order, order_id).status == "SHIPPED"


def test_admin_order_list_links_to_the_full_order(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/order/").get_data(as_text=True)
    assert f"/admin/order/details/?id={order_id}" in html and f"BZ-{order_id:06d}" in html
    assert "Lovelace" in html and "Guest" in html  # customer column from the shipping address
    assert "bz-status--placed" in html


def test_admin_order_details_show_the_whole_order(app, client, product_ids):
    _, order_id = checkout(app, app.test_client(), product_ids)
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get(f"/admin/order/details/?id={order_id}").get_data(as_text=True)
    for text in [
        "Gold Signet",
        "Ring size 6",
        "FLOW-RING",
        "$99.99",
        "Subtotal",
        "Total",
        "1 Main St",
        "Albany",
        "ada@example.com",
        "Cash on delivery",
        "Morning",
        "Mark shipped",
        "Cancel order",
        "Print packing slip",
    ]:
        assert text in html, text
    assert "Mark delivered" not in html  # only next steps for a PLACED order are offered
    client.post(f"/admin/order/status/{order_id}", data={"status": "SHIPPED"})
    html = client.get(f"/admin/order/details/?id={order_id}").get_data(as_text=True)
    assert "Mark delivered" in html and "Mark shipped" not in html
    assert "moved from Placed to Shipped" in html  # confirmation message


def test_order_items_screen_is_folded_into_the_order_page(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert client.get("/admin/orderitem/").status_code == 404
