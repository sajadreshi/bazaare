"""Admin dashboard: sales numbers, orders to ship, recent orders and catalog to-dos."""

from datetime import timedelta
from decimal import Decimal

from app.extension import db
from app.models import Customer, Order, OrderItem, Product, utcnow
from app.services.dashboard import build_dashboard
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login


def _order(customer_id, total, days_ago=0, status="PLACED", name="Dash Ring"):
    order = Order(
        customer_id=customer_id,
        status=status,
        total=Decimal(total),
        total_merchandise=Decimal(total),
        placed_at=utcnow() - timedelta(days=days_ago),
    )
    order.items.append(OrderItem(sku="DASH-1", name=name, price=Decimal(total)))
    db.session.add(order)
    return order


def test_dashboard_numbers(app):
    with app.app_context():
        customer = Customer(id=9100000001, customer_type="GUEST")
        db.session.add(customer)
        db.session.flush()
        before = build_dashboard()
        _order(customer.id, "40.00", 0)
        _order(customer.id, "60.00", 2, status="SHIPPED")
        _order(customer.id, "25.00", 9)  # previous week
        _order(customer.id, "999.00", 1, status="CANCELLED")  # never counted
        db.session.commit()
        dash = build_dashboard()
        assert dash.today.orders == before.today.orders + 1
        assert dash.week.revenue - before.week.revenue == Decimal("100.00")
        assert dash.previous_week.revenue - before.previous_week.revenue == Decimal("25.00")
        assert dash.to_ship - before.to_ship == 2  # two PLACED (the cancelled one isn't)
        assert len(dash.daily) == 14 and dash.daily[-1][0] == utcnow().date()
        assert any(name == "Dash Ring" for name, *_ in dash.top_products)


def test_catalog_todos_flag_products_without_photo_or_category(app):
    with app.app_context():
        db.session.add(
            Product(sku="DASH-NOPHOTO", name="No Photo", compare_at_price=5, price=5, is_active=True)
        )
        db.session.commit()
        messages = " | ".join(message for message, *_ in build_dashboard().todos)
    assert (
        "without a photo" in messages and "in no category" in messages and "Empty menu categories" in messages
    )


def test_dashboard_page(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/").get_data(as_text=True)
    for text in [
        "Dashboard",
        "Orders to ship",
        "Sales, last 14 days",
        "Catalog to-do",
        "Recent orders",
        "+ Add product",
    ]:
        assert text in html, text
    assert ">Home<" not in html  # the menu item is now Dashboard
    assert "/static/css/admin.css" in html


def test_dashboard_needs_an_admin(client):
    assert client.get("/admin/").headers["Location"].startswith("/admin/login")
