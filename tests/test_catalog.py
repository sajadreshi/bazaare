"""Catalog and home page rendering from the catalog service."""

import re
from decimal import Decimal

import pytest

from app.extension import db
from app.models import (
    Attribute,
    Carousel,
    Category,
    Product,
    ProductAssociation,
    ProductAttribute,
    Variant,
)


@pytest.fixture(scope="module")
def catalog(app):
    with app.app_context():
        necklaces = Category.query.filter_by(code="NECK-NECKLACES").one()
        earrings = Category.query.filter_by(code="EARRINGS").one()
        hidden_cat = Category(code="HIDDEN", name="Hidden Things", is_active=False)

        pendant = Product(
            sku="CAT-PENDANT",
            name="Moon Pendant",
            description="A silver crescent.",
            retail_price=Decimal("80"),
            sale_price=Decimal("64.50"),
            material="Silver",
            is_active=True,
            is_sustainable=True,
            main_image="moon.png",
            alt1_image="moon-side.png",
        )
        studs = Product(
            sku="CAT-STUDS",
            name="Pearl Studs",
            retail_price=Decimal("40"),
            sale_price=Decimal("30.00"),
            is_active=True,
        )
        retired = Product(
            sku="CAT-RETIRED", name="Retired Hoop", retail_price=1, sale_price=1, is_active=False
        )
        secret = Product(sku="CAT-SECRET", name="Secret Ring", retail_price=1, sale_price=1, is_active=True)
        pendant.categories.append(necklaces)
        studs.categories.append(earrings)
        retired.categories.append(earrings)
        secret.categories.append(hidden_cat)

        chain_16 = Variant(size="16 inch", quantity=1, is_default=False)
        chain_18 = Variant(
            size="18 inch", quantity=Decimal("1.20"), is_default=True, description="Most popular"
        )
        one = Variant(size="One size", quantity=1, is_default=True)
        for v in (chain_16, chain_18):
            v.products.append(pendant)
        one.products.append(studs)

        stone = Attribute(attribute_name="Stone", attribute_value="Moonstone")
        db.session.add_all([pendant, studs, retired, secret, chain_16, chain_18, one, stone, hidden_cat])
        db.session.flush()
        db.session.add(ProductAttribute(product_id=pendant.id, attribute_id=stone.id))
        db.session.add(
            ProductAssociation(
                source_product_id=pendant.id,
                target_product_id=studs.id,
                association_type="XSELL",
                is_active=True,
            )
        )
        db.session.add(
            ProductAssociation(
                source_product_id=pendant.id,
                target_product_id=retired.id,
                association_type="XSELL",
                is_active=True,
            )
        )

        slide1 = Carousel(
            name="s1",
            header="New Moon Collection",
            text="<p>Hand <b>made</b></p>",
            position=1,
            image="home/2026/11/moon.jpg",
        )
        slide2 = Carousel(name="s2", header="Pearls are back", text="Classic studs", position=2)
        draft = Carousel(name="draft", header="Not ready yet", text="Hidden", is_active=False)
        db.session.add_all([slide1, slide2, draft])
        db.session.commit()
        return {"pendant": pendant.id, "studs": studs.id, "retired": retired.id, "chain_18": chain_18.id}


def test_category_pages_show_only_active_categories_and_products(client, catalog):
    html = client.get("/catalog/c/neckpieces").get_data(as_text=True)  # parent page includes children
    assert "Moon Pendant" in html
    html = client.get("/catalog/c/earrings").get_data(as_text=True)
    assert "Pearl Studs" in html
    assert "Retired Hoop" not in html  # inactive product
    assert client.get("/catalog/c/hidden").status_code == 404  # inactive category
    assert client.get("/catalog/collection").headers["Location"].endswith("/catalog/c/collections")


def test_product_page_shows_variants_attributes_and_cross_sells(client, catalog):
    html = client.get(f"/catalog/product/{catalog['pendant']}").get_data(as_text=True)
    assert "Moon Pendant" in html and "Silver" in html and "Moonstone" in html
    assert "$64.50" in html and "$77.40" in html  # 18 inch = 1.20 x 64.50
    assert re.search(rf'value="{catalog["chain_18"]}"[^>]*checked', html)  # default variant preselected
    assert "Most popular" in html
    assert "moon-side.png" in html  # alternate image thumbnail
    assert "Complete the look" in html and "Pearl Studs" in html
    assert "Retired Hoop" not in html  # inactive cross-sell hidden


def test_inactive_product_page_says_unavailable(client, catalog):
    html = client.get(f"/catalog/product/{catalog['retired']}").get_data(as_text=True)
    assert "Product does not exist or is currently out of stock" in html


def test_home_banner_shows_active_slides_in_order_with_their_images(client, catalog):
    html = client.get("/").get_data(as_text=True)
    assert html.index("New Moon Collection") < html.index("Pearls are back") < html.index("Shop by category")
    assert "Not ready yet" not in html  # inactive slide
    assert "Hand made" in html and "<b>made</b>" not in html  # rich text shown as plain text
    assert html.count('data-slide-to="') == 2
    assert 'src="/media/home/2026/11/moon.jpg"' in html  # the slide's own background image
    assert "Heritage, made to be worn every day" not in html  # default message replaced by the slides
    assert 'href="/catalog/c/neckpieces"' in html  # shop-by-category tiles


def test_admin_slides_form_explains_each_field(client):
    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
    from tests.test_security import login

    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/carousel/new/").get_data(as_text=True)
    assert "Background image (behind the headline)" in html and 'type="file"' in html
    assert "Order (lowest first)" in html and "Active (shown on the home page)" in html
    assert client.get("/admin/homepagecontent/").status_code == 404  # screen removed
