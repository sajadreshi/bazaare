"""Reports: date ranges in New York time, sales totals, products, coupons, customers, stock, tax, CSV."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.extension import db
from app.models import Address, Customer, Order, OrderItem, Product, Variant
from app.services import reports
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login

MARCH = {"range": "custom", "start": "2020-03-01", "end": "2020-03-31"}


def order(
    customer, placed, items, status="PLACED", coupon=None, discount="0", tax="0", state="NY", email="a@x.com"
):
    address = Address(
        first_name="Ann",
        last_name="Lee",
        address1="1 A St",
        city="hempstead",
        state=state,
        zip="11550",
        email=email,
    )
    merch = sum(Decimal(p) for _, p in items)
    o = Order(
        customer_id=customer,
        status=status,
        placed_at=placed,
        total_merchandise=merch,
        total_discount=Decimal(discount),
        total_shipping=Decimal("5.99"),
        total_taxes=Decimal(tax),
        total=merch - Decimal(discount) + Decimal("5.99") + Decimal(tax),
        coupon_code=coupon,
        tax_state="NY" if Decimal(tax) else None,
        shipping_address=address,
    )
    for name, price in items:
        o.items.append(OrderItem(sku=f"R-{name}", name=name, price=Decimal(price), variant_name="One Size"))
    db.session.add(o)
    return o


@pytest.fixture(scope="module")
def march(app):
    with app.app_context():
        for cid in (8800001, 8800002):
            if db.session.get(Customer, cid) is None:
                db.session.add(Customer(id=cid))
        db.session.flush()
        # 1 Mar 03:00 UTC is still 29 Feb in New York: belongs to February.
        order(8800001, datetime(2020, 3, 1, 3, 0), [("Moon Ring", "40")])
        order(
            8800001,
            datetime(2020, 3, 2, 15, 0),
            [("Moon Ring", "40"), ("Sun Studs", "20")],
            coupon="SAVE10",
            discount="6",
            tax="4.81",
        )
        order(8800002, datetime(2020, 3, 15, 15, 0), [("Sun Studs", "20")], email="b@x.com", state="NJ")
        order(
            8800002, datetime(2020, 3, 20, 15, 0), [("Moon Ring", "40")], status="CANCELLED", email="b@x.com"
        )
        db.session.commit()


def rng(args=None):
    return reports.parse_range(args or MARCH)


def test_ranges(app):
    today = date(2026, 11, 22)
    r = reports.parse_range({"range": "last_month"}, today=today)
    assert (r.start, r.end, r.group) == (date(2026, 10, 1), date(2026, 10, 31), "day")
    assert reports.parse_range({"range": "this_year"}, today=today).group == "month"
    r = reports.parse_range({"range": "custom", "start": "2020-03-31", "end": "2020-03-01"}, today=today)
    assert (r.start, r.end) == (date(2020, 3, 1), date(2020, 3, 31))  # swapped into order
    assert r.previous().end == date(2020, 2, 29)


def test_sales_summary_counts_new_york_days_and_skips_cancelled(app, march):
    with app.app_context():
        report = reports.sales(rng())
        t = report.totals
        assert (t.orders, t.items, t.gross, t.discounts, t.net) == (
            2,
            3,
            Decimal("80"),
            Decimal("6"),
            Decimal("74"),
        )
        assert t.tax == Decimal("4.81") and t.shipping == Decimal("11.98")
        assert (report.cancelled, report.cancelled_total) == (1, Decimal("45.99"))
        assert report.previous.orders == 1  # the 1 March 03:00 UTC order fell on 29 Feb in New York
        assert len(report.periods) == 31 and report.change("orders") == 100


def test_products_categories_and_unsold(app, march):
    with app.app_context():
        ranked, unsold = reports.products(rng())
        assert [(r.name, r.units, r.revenue) for r in ranked][:2] == [
            ("Sun Studs", 2, Decimal("40")),  # same revenue: more units first
            ("Moon Ring", 1, Decimal("40")),
        ]


def test_coupons_customers_and_tax(app, march):
    with app.app_context():
        rows, without = reports.coupons(rng())
        assert rows == [("SAVE10", [1, Decimal("6"), Decimal("54")])]
        assert (without.orders, without.net) == (1, Decimal("20"))
        customers = reports.customers(rng())
        assert (customers.new, customers.returning) == (1, 1)  # customer 1 had a February order
        assert {(p[0], p[1]) for p in customers.places} == {("NY", "Hempstead"), ("NJ", "Hempstead")}
        assert reports.tax(rng()) == [
            ("2020-03", "NY", 1, Decimal("54"), Decimal("5.99"), Decimal("4.81"), Decimal("0"))
        ]


def test_inventory_value(app):
    with app.app_context():
        product = Product(sku="INV-VAL", name="Value Cuff", price=Decimal("25"), is_active=True)
        product.options = [
            Variant(name="Silver", stock=4),
            Variant(name="Gold", stock=2, price=Decimal("30")),
        ]
        db.session.add(product)
        db.session.commit()
        rows, units, value = reports.inventory(rng())
        row = next(r for r in rows if r.product.sku == "INV-VAL")
        assert (row.in_stock, row.value) == (6, Decimal("160"))  # 4 x 25 + 2 x 30
        assert units >= 6 and value >= Decimal("160")


def test_reports_pages_and_csv_downloads(app, march):
    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    query = "range=custom&start=2020-03-01&end=2020-03-31"
    for tab in ("sales", "products", "categories", "coupons", "customers", "inventory", "tax"):
        page = admin.get(f"/admin/reports/?tab={tab}&{query}")
        assert page.status_code == 200, tab
        download = admin.get(f"/admin/reports/{tab}.csv?{query}")
        assert download.status_code == 200 and download.mimetype == "text/csv", tab
        assert f"bazaare-{tab}-20200301-20200331.csv" in download.headers["Content-Disposition"]
    sales_csv = admin.get(f"/admin/reports/sales.csv?{query}").get_data(as_text=True).splitlines()
    assert sales_csv[0].startswith("Period,Orders,Items,Gross sales")
    assert sales_csv[-1] == "Total,2,3,80.00,6.00,74.00,11.98,4.81,90.79,45.40"
    html = admin.get(f"/admin/reports/?tab=sales&{query}").get_data(as_text=True)
    assert "$74.00" in html and "1 cancelled" in html
    assert admin.get("/admin/reports/nope.csv").status_code == 404
