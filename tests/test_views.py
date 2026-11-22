from app.extension import db
from app.models import Category, Product, Variant


def test_jewellery_seed(app):
    with app.app_context():
        codes = {c.code for c in Category.query.all()}
        assert {"ACC-RINGS", "NECK-NECKLACES", "EARRINGS", "ACC-BANGLES", "GIFT-UNDER-25"} <= codes
        top = {c.code for c in Category.query.filter_by(parent_id=None)}
        assert {"NEW", "EARRINGS", "NECKPIECES", "ACCESSORIES", "SALE"} <= top
        rings = Category.query.filter_by(code="ACC-RINGS").one()
        assert rings.parent.code == "ACCESSORIES"


def test_public_pages(client):
    for url in [
        "/",
        "/about",
        "/catalog/c/collections",
        "/catalog/search?q=ring",
        "/catalog/wishlist",
        "/auth/login",
        "/auth/register",
    ]:
        resp = client.get(url)
        assert resp.status_code == 200, url
    assert b"Bazaare" in client.get("/about").data


def test_product_page_shows_jewellery_fields(app, client):
    with app.app_context():
        rings = Category.query.filter_by(code="ACC-RINGS").one()
        product = Product(
            sku="RING-001",
            name="Silver Band",
            compare_at_price=49.0,
            price=39.0,
            material="Sterling silver",
            is_handmade=True,
            is_active=True,
        )
        product.categories.append(rings)
        product.options = [Variant(stock=1000, name="Ring size 7", is_default=True)]
        db.session.add(product)
        db.session.commit()
        pid = product.id
    resp = client.get(f"/catalog/product/{pid}")
    assert resp.status_code == 200
    assert b"Sterling silver" in resp.data
    assert b"Ring size 7" in resp.data
    resp = client.get("/catalog/c/accessories")
    assert b"Silver Band" in resp.data


def test_add_to_cart(app, client):
    with app.app_context():
        product = Product.query.filter_by(sku="RING-001").one()
        pid, vid = product.id, product.options[0].id
    resp = client.post(f"/catalog/product/{pid}", data={"pid": pid, "size": vid})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Added to your bag" in html and "data-bz-drawer" in html and "Silver Band" in html
    assert "data-bz-drawer" not in client.get(f"/catalog/product/{pid}").get_data(as_text=True)
    resp = client.get("/checkout/shopcart")
    assert resp.status_code == 200
    assert b"Silver Band" in resp.data
