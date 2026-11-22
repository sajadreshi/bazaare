"""Inventory: selling the last piece hides a product, restocking brings it back, and the shop threshold."""

from decimal import Decimal

import pytest

from app.extension import db
from app.models import Category, Order, Product, ShopSettings, Variant
from app.services import inventory
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_product_editor import place
from tests.test_security import login

counter = iter(range(1000))


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
            row.stock_threshold, row.low_stock_alert = 0, 3
            db.session.commit()


def make(app, *stocks, active=True):
    """A product in Earrings with one option per stock count; returns (product id, [option ids])."""
    with app.app_context():
        product = Product(
            sku=f"INV-{next(counter)}", name="Inventory Hoops", price=Decimal("20"), is_active=active
        )
        product.categories = [Category.query.filter_by(code="EARRINGS").one()]
        product.options = [
            Variant(name=f"Design {i}", stock=s, is_default=i == 0) for i, s in enumerate(stocks)
        ]
        db.session.add(product)
        db.session.commit()
        return product.id, [o.id for o in product.options]


def product(app, pid):
    with app.app_context():
        p = db.session.get(Product, pid)
        return p.is_active, p.sold_out_at is not None, [o.stock for o in p.options]


def buy(client, pid, vid):
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": vid})
    return place(client)


def test_selling_the_last_piece_hides_the_product_and_cancelling_brings_it_back(app, client, admin):
    pid, [vid] = make(app, 1)
    assert "/checkout/confirm/" in buy(client, pid, vid).headers["Location"]
    assert product(app, pid) == (False, True, [0])
    assert client.get(f"/catalog/product/{pid}").status_code == 200
    assert "Inventory Hoops" not in client.get("/catalog/c/earrings").get_data(as_text=True)

    with app.app_context():
        order_id = Order.query.order_by(Order.id.desc()).first().id
    admin.post(f"/admin/order/status/{order_id}", data={"status": "CANCELLED"})
    assert product(app, pid) == (True, False, [1])
    admin.post(f"/admin/order/status/{order_id}", data={"status": "PLACED"})
    assert product(app, pid) == (False, True, [0])


def test_a_product_stays_on_sale_while_any_option_has_stock(app, client):
    pid, [first, second] = make(app, 1, 3)
    buy(client, pid, first)
    assert product(app, pid) == (True, False, [0, 3])


def test_threshold_keeps_a_reserve_and_hides_products_at_it(app, client, admin):
    pid, [vid] = make(app, 3)
    resp = admin.post("/admin/settings/", data={"stock_threshold": "2", "low_stock_alert": "3"})
    assert resp.status_code == 302
    assert product(app, pid)[0] is True  # 1 above the reserve can still be sold
    html = client.get(f"/catalog/product/{pid}").get_data(as_text=True)
    assert "Only 1 left" in html
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": vid})
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": vid})  # a second one is refused
    with client.session_transaction() as sess:
        assert any("only 1" in m for _, m in sess.get("_flashes", []))
    place(client)
    assert product(app, pid) == (False, True, [2])  # the reserve of 2 stays in the drawer

    admin.post("/admin/settings/", data={"stock_threshold": "0", "low_stock_alert": "3"})
    assert product(app, pid) == (True, False, [2])  # lowering the reserve puts it back on sale


def test_restocking_in_admin_brings_back_a_sold_out_product_but_not_one_hidden_by_hand(app, admin):
    sold_out, [opt] = make(app, 0)
    with app.app_context():
        inventory.refresh([db.session.get(Product, sold_out)])
        db.session.commit()
    assert product(app, sold_out) == (False, True, [0])
    listing = admin.get("/admin/product/").get_data(as_text=True)
    assert "sold out · hidden" in listing
    # Showing it by hand is refused while there's nothing to sell.
    admin.post(f"/admin/product/toggle/{sold_out}", data={"next": "/admin/product/"})
    assert product(app, sold_out)[0] is False

    with app.app_context():
        sku = db.session.get(Product, sold_out).sku
    form = {
        "name": "Inventory Hoops",
        "sku": sku,
        "price": "20",
        "options-0-id": str(opt),
        "options-0-name": "Design 0",
        "options-0-stock": "4",
    }
    assert admin.post(f"/admin/product/edit/?id={sold_out}", data=form).status_code == 302
    assert product(app, sold_out) == (True, False, [4])

    # Hidden by hand: restocking doesn't bring it back.
    admin.post(f"/admin/product/toggle/{sold_out}", data={"next": "/admin/product/"})
    form["options-0-stock"] = "9"
    admin.post(f"/admin/product/edit/?id={sold_out}", data=form)
    assert product(app, sold_out) == (False, False, [9])


def test_dashboard_lists_stock_to_dos(app, admin):
    make(app, 2)
    make(app, None)
    html = admin.get("/admin/").get_data(as_text=True)
    assert "Running low" in html and "Options without a stock count" in html


def test_stock_page_updates_many_options_at_once(app, admin):
    a, [a1] = make(app, None)
    b, [b1, b2] = make(app, 0, 0)
    with app.app_context():
        inventory.refresh([db.session.get(Product, b)])
        db.session.commit()
    html = admin.get("/admin/stock/?show=missing").get_data(as_text=True)
    assert f'name="stock-{a1}"' in html and f'name="stock-{b1}"' not in html
    resp = admin.post(
        "/admin/stock/?show=all", data={f"stock-{a1}": "6", f"stock-{b2}": "2", f"stock-{b1}": ""}
    )
    assert resp.status_code == 302
    assert product(app, a) == (True, False, [6])
    assert product(app, b) == (True, False, [0, 2])  # restocked: back in the shop
    admin.post("/admin/stock/", data={f"stock-{a1}": "lots"})
    assert product(app, a)[2] == [6]  # not a number: nothing saved
