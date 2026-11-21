"""Catalog and home page rendering from the catalog service."""

import re
from decimal import Decimal

import pytest

from app.extension import db
from app.models import (
    Attribute,
    Carousel,
    Category,
    HomePageContent,
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

        slide1 = Carousel(name="s1", header="New Moon Collection", text="<p>Hand <b>made</b></p>")
        slide2 = Carousel(name="s2", header="Pearls are back", text="Classic studs")
        home = HomePageContent(is_active=True, category=earrings)
        home.carousel.append(slide1)
        home.carousel.append(slide2)
        db.session.add_all([slide1, slide2, home])
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


def test_home_page_renders_slides_featured_and_collection(client, catalog):
    html = client.get("/").get_data(as_text=True)
    assert "New Moon Collection" in html and "Pearls are back" in html
    assert "Hand made" in html and "<b>made</b>" not in html  # rich text shown as plain text
    assert html.count('data-slide-to="') == 2
    assert "Pearl Studs" in html  # featured category chosen in the admin (earrings)
    assert 'href="/catalog/c/neckpieces"' in html  # shop-by-category tiles
    assert "Secret Ring" not in html


def test_home_banner_uses_the_admin_hero_image_and_slides(app, client, catalog):
    with app.app_context():
        home = HomePageContent.query.filter_by(is_active=True).order_by(HomePageContent.id.desc()).first()
        home.hero_image = "home/2026/11/banner.jpg"
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    assert 'class="bz-hero__img" src="/media/home/2026/11/banner.jpg"' in html
    assert html.index("New Moon Collection") < html.index("Shop by category")  # slides are in the top banner
    assert "Heritage, made to be worn every day" not in html  # default message replaced by the slides
    assert '<h2 class="bz-title">Earrings</h2>' in html  # featured section titled after its category


def test_admin_home_content_form_explains_each_field(client):
    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
    from tests.test_security import login

    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/homepagecontent/new/").get_data(as_text=True)
    assert "Slides (headline + message rotating in the top banner)" in html
    assert "Featured category" in html and 'type="file"' in html
