from app.extension import db
from app.models import Category, Collection, Product, Variant


def test_jewellery_seed(app):
    with app.app_context():
        codes = {c.code for c in Category.query.all()}
        assert {"RINGS", "NECKLACES", "EARRINGS", "BRACELETS"} <= codes
        jewellery = Collection.query.filter_by(name="Jewellery").one()
        assert jewellery.category.count() == 4


def test_public_pages(client):
    for url in ["/", "/about", "/catalog/collection", "/auth/login", "/auth/register"]:
        resp = client.get(url)
        assert resp.status_code == 200, url
    assert b"Bazaare" in client.get("/about").data


def test_product_page_shows_jewellery_fields(app, client):
    with app.app_context():
        rings = Category.query.filter_by(code="RINGS").one()
        variant = Variant(size="Ring size 7", quantity=1, is_default=True)
        product = Product(sku="RING-001", name="Silver Band", retail_price=49.0, sale_price=39.0,
                          material="Sterling silver", is_handmade=True, is_active=True, display=True)
        product.categories.append(rings)
        variant.products.append(product)
        db.session.add_all([product, variant])
        db.session.commit()
        pid = product.id
    resp = client.get(f"/catalog/product/{pid}")
    assert resp.status_code == 200
    assert b"Sterling silver" in resp.data
    assert b"Ring size 7" in resp.data
    resp = client.get("/catalog/collection")
    assert b"Silver Band" in resp.data
