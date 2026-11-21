"""Storefront: menu, category pages with price rules, search, wishlist and the catalog import."""

import io
import json

from PIL import Image

from app.catalog_import import import_catalog
from app.extension import db
from app.models import Category, Product


def test_menu_shows_top_level_items_with_dropdowns(client):
    html = client.get("/").get_data(as_text=True)
    for name in [
        "New Arrivals",
        "Collections",
        "Earrings",
        "Neckpieces",
        "Accessories",
        "Bestsellers",
        "Gifting",
        "Sale",
    ]:
        assert f"<span>{name}</span>" in html, name
    for sub in ["Jhumkas", "Chandbalis", "Hasli", "Bangles", "Under $25", "Festive Offers", "Meenakari"]:
        assert f">{sub}</a>" in html, sub
    assert "Jewellery · Craft · Culture" in html


def _product(sku, price, *codes, compare_at=None, name=None):
    product = Product(
        sku=sku, name=name or sku, retail_price=compare_at or price, sale_price=price, is_active=True
    )
    product.categories = [Category.query.filter_by(code=c).one() for c in codes]
    db.session.add(product)
    return product


def test_price_rule_categories_and_sale_badges(app, client):
    with app.app_context():
        _product("SF-CHEAP", 19, "EAR-STUDS", name="Tiny Studs")
        _product("SF-MID", 45, "NECK-HASLI", name="Mid Hasli")
        _product("SF-SALE", 30, "SALE-FESTIVE", compare_at=40, name="Festive Drop")
        db.session.commit()
    under25 = client.get("/catalog/c/gift-under-25").get_data(as_text=True)
    assert "Tiny Studs" in under25 and "Mid Hasli" not in under25
    assert "Mid Hasli" in client.get("/catalog/c/gift-under-50").get_data(as_text=True)
    sale = client.get("/catalog/c/sale").get_data(as_text=True)  # parent page includes Festive Offers
    assert "Festive Drop" in sale and "$40.00" in sale and "bz-card__tag" in sale
    page = client.get("/catalog/c/gift-under-50?sort=price-desc").get_data(as_text=True)
    assert page.index("Mid Hasli") < page.index("Tiny Studs")


def test_empty_category_says_coming_soon(client):
    html = client.get("/catalog/c/ear-cuffs").get_data(as_text=True)
    assert "New pieces are on their way" in html


def test_search_matches_words_in_name_description_and_category(app, client):
    with app.app_context():
        p = _product("SF-SEARCH", 25, "EAR-JHUMKAS", name="Moonlit Jhumka")
        p.description = "Oxidised bells and a turquoise stone."
        db.session.commit()
    assert "Moonlit Jhumka" in client.get("/catalog/search?q=turquoise").get_data(as_text=True)
    assert "Moonlit Jhumka" in client.get("/catalog/search?q=jhumkas moonlit").get_data(as_text=True)
    assert "No pieces match" in client.get("/catalog/search?q=zzzz").get_data(as_text=True)


def test_wishlist_toggle(app, client):
    with app.app_context():
        product = _product("SF-WISH", 22, "ACC-RINGS", name="Wishful Ring")
        db.session.commit()
        pid = product.id
    resp = client.post(f"/catalog/wishlist/{pid}", headers={"Accept": "application/json"})
    assert resp.get_json() == {"added": True, "count": 1}
    page = client.get("/catalog/wishlist").get_data(as_text=True)
    assert "Wishful Ring" in page and 'class="bz-badge">1<' in page
    client.post(f"/catalog/wishlist/{pid}")
    assert "Nothing saved yet" in client.get("/catalog/wishlist").get_data(as_text=True)


def test_import_catalog_creates_products_with_designs_and_photos(app, tmp_path):
    for name in ("a.jpg", "b.jpg", "banner.jpg"):
        buf = io.BytesIO()
        Image.new("RGB", (600, 600), "gold").save(buf, "JPEG")
        (tmp_path / name).write_bytes(buf.getvalue())
    manifest = {
        "banners": {"EARRINGS": "banner.jpg"},
        "associations": [{"source": "IMP-1", "target": "IMP-2", "type": "UPSELL", "position": 1}],
        "products": [
            {
                "sku": "IMP-1",
                "name": "Imported Jhumka",
                "price": 30,
                "compare_at": 36,
                "material": "Brass",
                "description": "Test.",
                "categories": ["EAR-JHUMKAS", "SALE-LAST"],
                "designs": ["Blue", "Green"],
                "images": ["a.jpg", "b.jpg"],
            },
            {
                "sku": "IMP-2",
                "name": "Imported Stud",
                "price": 18,
                "material": "Brass",
                "description": "Test.",
                "categories": ["EAR-STUDS"],
                "designs": [],
                "images": ["a.jpg"],
            },
        ],
    }
    path = tmp_path / "products.json"
    path.write_text(json.dumps(manifest))
    with app.app_context():
        assert import_catalog(str(path), str(tmp_path)) == (2, 0, 0)
        assert import_catalog(str(path), str(tmp_path)) == (0, 0, 2)  # idempotent
        jhumka = Product.query.filter_by(sku="IMP-1").one()
        assert [(a.target_product.sku, a.association_type) for a in jhumka.associations] == [
            ("IMP-2", "UPSELL")
        ]
        assert sorted(v.size for v in jhumka.variant) == ["Blue", "Green"]
        assert jhumka.main_image and jhumka.alt1_image and not jhumka.alt2_image
        assert (jhumka.sale_price, jhumka.retail_price) == (30, 36)
        assert [v.size for v in Product.query.filter_by(sku="IMP-2").one().variant] == ["One Size"]
        assert Category.query.filter_by(code="EARRINGS").one().banner_image.startswith("banners/")
        # --update refreshes text but keeps photos
        manifest["products"][0]["name"] = "Renamed Jhumka"
        path.write_text(json.dumps(manifest))
        photo = jhumka.main_image
        assert import_catalog(str(path), str(tmp_path), update=True) == (0, 2, 0)
        jhumka = Product.query.filter_by(sku="IMP-1").one()
        assert (jhumka.name, jhumka.main_image) == ("Renamed Jhumka", photo)


def test_client_manifest_is_valid(app):
    # Every product in the real manifest points at real menu categories.
    with open("data/catalog/products.json") as fh:
        manifest = json.load(fh)
    with app.app_context():
        codes = {c.code for c in Category.query.all()}
    assert len(manifest["products"]) >= 50
    skus = {item["sku"] for item in manifest["products"]}
    for link in manifest["associations"]:
        assert link["source"] in skus and link["target"] in skus and link["type"] in ("XSELL", "UPSELL"), link
    for item in manifest["products"]:
        assert set(item["categories"]) <= codes, item["sku"]
        assert item["images"] and item["description"] and item["price"] > 0
