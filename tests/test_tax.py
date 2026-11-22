"""Sales tax: rate lookup by ZIP, loading rate files, tax at checkout and on orders, admin page."""

import io
from decimal import Decimal

import pytest

from app.extension import db
from app.models import Address, Order, TaxRate, TaxState
from app.services import tax
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import REFERER, add_to_cart, address
from tests.test_security import login

AVALARA = (
    "State,ZipCode,TaxRegionName,EstimatedCombinedRate,StateRate,EstimatedCountyRate,"
    "EstimatedCityRate,EstimatedSpecialRate,RiskLevel\n"
    "NY,11530,NASSAU COUNTY,0.086250,0.040000,0.042500,0.000000,0.003750,1\n"
    "NY,12207,ALBANY COUNTY,0.080000,0.040000,0.040000,0.000000,0.000000,1\n"
    "NY,10001,NEW YORK CITY,0.088750,0.040000,0.000000,0.045000,0.003750,1\n"
)


@pytest.fixture
def new_york(app):
    """Collect tax in NY (shipping taxable) with a small rate table; removed afterwards."""
    with app.app_context():
        db.session.add(
            TaxState(state="NY", collect=True, tax_shipping=True, fallback_rate=Decimal("0.08625"))
        )
        tax.load_rates(AVALARA, source="test.csv")
        db.session.commit()
    yield
    with app.app_context():
        db.session.query(TaxRate).delete()
        db.session.query(TaxState).delete()
        db.session.commit()


def quote(state, zip_code):
    return tax.quote(Address(state=state, zip=zip_code))


def test_rate_comes_from_the_zip_then_the_state_standard_rate(app, new_york):
    with app.app_context():
        nassau = quote("NY", "11530-1234")
        assert (nassau.rate, nassau.region, nassau.percent, nassau.tax_shipping) == (
            Decimal("0.086250"),
            "NASSAU COUNTY",
            "8.625%",
            True,
        )
        assert quote("NY", "10001").percent == "8.875%"
        unknown = quote("NY", "14850")  # not in the table: the state's standard rate
        assert unknown.rate == Decimal("0.08625") and "standard" in unknown.region
        assert not quote("CA", "90210").applies  # the shop doesn't collect in California
        assert not tax.quote(None).applies
        assert nassau.on(Decimal("99.99")) == Decimal("8.62")


def test_rate_files_replace_a_states_zips_and_bad_files_are_refused(app, new_york):
    with app.app_context():
        counts = tax.load_rates("zip,state,rate\n11530,NY,8.5\n", source="mine.csv")
        assert counts == {"NY": 1}
        assert db.session.query(TaxRate).count() == 1  # the old NY rows were replaced
        assert quote("NY", "11530").rate == Decimal("0.085000")
        for bad in ("hello,world\n1,2\n", "zip,state,rate\n11530,NY,abc\n", "zip,state,rate\n11530,NY,75\n"):
            with pytest.raises(tax.RateFileError):
                tax.load_rates(bad)
        db.session.rollback()


def checkout(client, method="STANDARD", state="NY", zip_code="11530"):
    ship = {**address("shipping_form"), "state": state, "zip": zip_code}
    client.post("/checkout/order", data=ship, headers=REFERER)
    client.post("/checkout/order", data={"form_id": "shipping_method_form", "shipping_method": method})
    return client.post("/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"})


def test_tax_is_added_at_checkout_on_merchandise_and_shipping(app, client, product_ids, new_york):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    assert "Calculated at checkout" in client.get("/checkout/shopcart").get_data(as_text=True)
    resp = checkout(client, method="EXPRESS")
    assert "/checkout/confirm/" in resp.headers["Location"]
    with app.app_context():
        order = Order.query.order_by(Order.id.desc()).first()
        # 99.99 + 14.99 shipping, both taxed at 8.625%: 8.62 + 1.29
        assert (order.total_taxes, order.shipping_tax, order.total) == (
            Decimal("9.91"),
            Decimal("1.29"),
            Decimal("124.89"),
        )
        assert (order.tax_state, order.tax_region, order.tax_rate) == (
            "NY",
            "NASSAU COUNTY",
            Decimal("0.086250"),
        )
        assert order.items[0].tax == Decimal("8.62")
        assert order.payments[0].approved_amount == Decimal("124.89")
        order_id = order.id
    html = client.get(f"/checkout/confirm/{order_id}").get_data(as_text=True)
    assert "Sales tax (8.625%)" in html and "$9.91" in html


def test_no_tax_when_shipping_to_a_state_the_shop_does_not_collect_in(app, client, product_ids, new_york):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    checkout(client, state="CA", zip_code="90210")
    with app.app_context():
        order = Order.query.order_by(Order.id.desc()).first()
        assert (order.total_taxes, order.tax_state, order.total) == (Decimal("0.00"), None, Decimal("99.99"))


def test_shipping_is_untaxed_where_the_state_says_so(app, client, product_ids, new_york):
    with app.app_context():
        db.session.get(TaxState, "NY").tax_shipping = False
        db.session.commit()
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    checkout(client, method="EXPRESS")
    with app.app_context():
        order = Order.query.order_by(Order.id.desc()).first()
        assert (order.total_taxes, order.shipping_tax) == (Decimal("8.62"), Decimal("0.00"))


def test_admin_taxes_page_uploads_rates_looks_up_zips_and_reports(app, client, product_ids, new_york):
    pid, small, _ = product_ids
    with app.app_context():
        add_to_cart(client, pid, small)
    checkout(client)
    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = admin.get("/admin/taxes/?zip=12207").get_data(as_text=True)
    assert "8%" in html and "ALBANY COUNTY" in html and "Tax collected" in html and "NY" in html
    upload = {"action": "upload", "rates": (io.BytesIO(b"zip,state,rate\n11701,NY,0.08625\n"), "ny.csv")}
    resp = admin.post("/admin/taxes/", data=upload, content_type="multipart/form-data")
    assert resp.status_code == 302
    with app.app_context():
        assert [r.zip for r in db.session.query(TaxRate)] == ["11701"]
        assert db.session.get(TaxState, "NY").rates_source == "ny.csv"
    form = {"action": "save", "collect-NY": "y", "fallback-NY": "8.875", "add_state": "NJ"}
    admin.post("/admin/taxes/", data=form)
    with app.app_context():
        ny = db.session.get(TaxState, "NY")
        assert (ny.tax_shipping, ny.fallback_rate) == (False, Decimal("0.088750"))
        assert db.session.get(TaxState, "NJ").collect is True


def test_tax_is_rounded_once_on_the_subtotal_and_split_across_lines(app, client, product_ids, new_york):
    from app.models import Cart, Item
    from app.services.cart import recalculate
    from app.services.tax import TaxQuote

    with app.app_context():
        cart = Cart(status="PENDING")
        prices = ["36.00", "34.00", "32.00", "30.00", "38.00", "33.00", "34.00", "34.00"]  # 271.00
        cart.items = [Item(product_sku="X", product_price=Decimal(p), status="PENDING") for p in prices]
        from app.services import cart as cart_service

        original = cart_service.tax.quote
        cart_service.tax.quote = lambda address: TaxQuote(Decimal("0.08625"), "NY", "TEST", True)
        try:
            recalculate(cart)
        finally:
            cart_service.tax.quote = original
        assert cart.total_taxes == Decimal("23.37")  # 271.00 x 8.625%, not the sum of rounded lines
        assert sum(i.merchandise_tax for i in cart.items) == Decimal("23.37")
        db.session.rollback()
