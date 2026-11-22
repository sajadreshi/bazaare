"""The product editor (options & stock, SKU, duplicate, show/hide), stock at checkout, categories."""

from decimal import Decimal

import pytest

from app.extension import db
from app.models import Category, Order, Product, ProductImage, Variant
from app.richtext import clean_html
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_checkout_flow import REFERER, address
from tests.test_security import login


@pytest.fixture
def admin_client(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return client


def option_rows(*rows):
    data = {}
    for i, row in enumerate(rows):
        for key, value in row.items():
            data[f"options-{i}-{key}"] = value
    return data


def test_options_are_saved_with_their_own_price_stock_order_and_one_default(app, admin_client):
    data = {
        "name": "Lotus Ring",
        "price": "40",
        "compare_at_price": "30",  # not higher than the price: no sale
        "option_label": "Size",
        "is_active": "y",
        "description": "<p>Hand <b>carved</b></p><script>alert(1)</script>",
        **option_rows(
            {"name": "Size 8", "price": "", "stock": "4", "position": "1"},
            {"name": "Size 6", "price": "44.50", "stock": "3", "position": "0", "is_default": "y"},
            {"name": "Size 7", "stock": "0", "position": "2", "is_default": "y"},
        ),
    }
    assert admin_client.post("/admin/product/new/", data=data).status_code == 302
    with app.app_context():
        product = Product.query.filter_by(name="Lotus Ring").one()
        assert product.sku == "BZ-LOTU-RING"
        assert product.compare_at_price is None
        assert product.description == "<p>Hand <strong>carved</strong></p>"
        assert [(o.name, o.price, o.stock) for o in product.options] == [
            ("Size 6", Decimal("44.50"), 3),
            ("Size 8", None, 4),
            ("Size 7", None, 0),
        ]
        assert [o.name for o in product.options if o.is_default] == ["Size 6"]
        pid = product.id

    html = admin_client.get(f"/catalog/product/{pid}").get_data(as_text=True)
    assert "Size" in html and "$44.50" in html
    assert "sold out" in html  # Size 7 is shown but can't be picked
    assert "Hand <strong>carved</strong>" in html and "<script>alert" not in html

    # The product list shows the stock picture and a show/hide switch.
    listing = admin_client.get("/admin/product/").get_data(as_text=True)
    assert "Lotus Ring" in listing and "7 available" in listing and "1 option(s) sold out" in listing


def test_every_option_needs_a_stock_count_and_a_product_needs_an_option(app, admin_client):
    data = {"name": "No Count Ring", "price": "40", **option_rows({"name": "Size 6", "stock": ""})}
    html = admin_client.post("/admin/product/new/", data=data).get_data(as_text=True)
    assert "How many do you have?" in html
    html = admin_client.post("/admin/product/new/", data={"name": "Empty Ring", "price": "40"}).get_data(
        as_text=True
    )
    assert "at least one row under Options" in html
    with app.app_context():
        assert Product.query.filter(Product.name.in_(["No Count Ring", "Empty Ring"])).count() == 0


def test_a_taken_sku_is_refused(app, admin_client, product_ids):
    data = {"name": "Copycat", "sku": "flow-ring", "price": "5"}
    resp = admin_client.post("/admin/product/new/", data=data)
    assert resp.status_code == 200
    assert "SKU FLOW-RING is already used by Gold Signet" in resp.get_data(as_text=True)


def test_duplicate_makes_a_hidden_copy_with_options_and_photos(app, admin_client):
    with app.app_context():
        source = Product(sku="DUP-1", name="Rose Studs", price=Decimal("20"), is_active=True)
        source.images = [ProductImage(image="products/rose.jpg", position=0)]
        source.options = [Variant(name="Rose", stock=5, is_default=True), Variant(name="Gold")]
        source.categories = [Category.query.filter_by(code="EARRINGS").one()]
        db.session.add(source)
        db.session.commit()
        sid = source.id
    resp = admin_client.post(f"/admin/product/duplicate/{sid}")
    assert resp.status_code == 302 and "/admin/product/edit/" in resp.headers["Location"]
    with app.app_context():
        copy = Product.query.filter_by(sku="DUP-1-COPY").one()
        assert copy.name == "Rose Studs (copy)" and copy.is_active is False
        assert copy.main_image == "products/rose.jpg"
        assert [(o.name, o.stock) for o in copy.options] == [("Rose", 0), ("Gold", None)]
        assert [c.code for c in copy.categories] == ["EARRINGS"]
        assert db.session.get(Product, sid).options[0].stock == 5  # source untouched


def test_list_switch_shows_and_hides_a_product(app, admin_client):
    with app.app_context():
        product = Product(sku="TOGGLE-1", name="Toggle", price=1, is_active=True)
        db.session.add(product)
        db.session.commit()
        pid = product.id
    admin_client.post(f"/admin/product/toggle/{pid}", data={"next": "/admin/product/"})
    with app.app_context():
        assert db.session.get(Product, pid).is_active is False
    admin_client.post(f"/admin/product/toggle/{pid}", data={"next": "https://evil.example/"})
    with app.app_context():
        assert db.session.get(Product, pid).is_active is True


@pytest.fixture
def limited(app):
    """A product with 2 in stock of one option and a sold-out one."""
    with app.app_context():
        product = Product(
            sku=f"STOCK-{Product.query.count()}", name="Limited Cuff", price=Decimal("25"), is_active=True
        )
        product.options = [Variant(name="Silver", stock=2, is_default=True), Variant(name="Gold", stock=0)]
        db.session.add(product)
        db.session.commit()
        return product.id, product.options[0].id, product.options[1].id


def flashes(client):
    with client.session_transaction() as sess:
        return [m for _, m in sess.pop("_flashes", [])]


def test_bag_refuses_sold_out_options_and_more_than_is_left(app, client, limited):
    pid, silver, gold = limited
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": gold})
    assert any("sold out" in m for m in flashes(client))
    for _ in range(2):
        assert client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": silver}).status_code == 200
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": silver})
    assert any("only 2" in m for m in flashes(client))


def place(client):
    for form in ("shipping_form", "billing_form"):
        client.post("/checkout/order", data=address(form), headers=REFERER)
    return client.post(
        "/checkout/order", data={"form_id": "place_order_form", "payment_method": "COD"}, headers=REFERER
    )


def test_placing_an_order_takes_stock_and_cancelling_puts_it_back(app, client, limited):
    pid, silver, _ = limited
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": silver})
    assert "/checkout/confirm/" in place(client).headers["Location"]
    with app.app_context():
        assert db.session.get(Variant, silver).stock == 1
        order_id = Order.query.order_by(Order.id.desc()).first().id

    admin = app.test_client()
    login(admin, ADMIN_EMAIL, ADMIN_PASSWORD)
    admin.post(f"/admin/order/status/{order_id}", data={"status": "CANCELLED"})
    with app.app_context():
        assert db.session.get(Variant, silver).stock == 2
    admin.post(f"/admin/order/status/{order_id}", data={"status": "PLACED"})
    with app.app_context():
        assert db.session.get(Variant, silver).stock == 1


def test_order_is_refused_if_stock_ran_out_meanwhile(app, client, limited):
    pid, silver, _ = limited
    client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": silver})
    with app.app_context():
        db.session.get(Variant, silver).stock = 0
        db.session.commit()
    place(client)
    assert any("just sold out" in m for m in flashes(client))
    with app.app_context():
        assert db.session.get(Variant, silver).stock == 0


def test_category_code_comes_from_the_name_and_parents_cannot_loop(app, admin_client):
    with app.app_context():
        earrings = Category.query.filter_by(code="EARRINGS").one().id
    resp = admin_client.post(
        "/admin/category/new/", data={"name": "Ear Cuffs & Climbers", "parent": str(earrings)}
    )
    assert resp.status_code == 302
    with app.app_context():
        cuffs = Category.query.filter_by(code="EAR-CUFFS-CLIMBERS").one()
        assert cuffs.parent.code == "EARRINGS"
        cuffs_id = cuffs.id
    page = admin_client.get("/admin/category/new/").get_data(as_text=True)
    assert "— Ear Cuffs &amp; Climbers" in page  # the parent picker shows the tree
    # Earrings can't move inside its own sub-category.
    resp = admin_client.post(
        f"/admin/category/edit/?id={earrings}",
        data={"name": "Earrings", "code": "EARRINGS", "parent": str(cuffs_id)},
    )
    assert "can&#39;t be inside itself" in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Category, earrings).parent_id is None


@pytest.mark.parametrize(
    "raw,clean",
    [
        ("Plain line\n\nSecond", "<p>Plain line</p><p>Second</p>"),
        ('<p style="x" onclick="y">Hi <a href="z">there</a></p>', "<p>Hi there</p>"),
        ("<ul><li>One<li>Two</ul>", "<ul><li>One</li><li>Two</li></ul>"),
        ("<p>Fish &amp; chips <3</p>", "<p>Fish &amp; chips &lt;3</p>"),
        ("<style>p{}</style><b>Bold</b>", "<strong>Bold</strong>"),
    ],
)
def test_descriptions_keep_only_simple_formatting(raw, clean):
    assert clean_html(raw) == clean
