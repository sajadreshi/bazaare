"""Product attributes: one type (Stone), a value per product, shown on the page and searchable."""

import re

from app.extension import db
from app.models import Attribute, Product, ProductAttribute
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login


def test_same_attribute_different_values_per_product(app, client):
    with app.app_context():
        metal = Attribute(name="Metal type", position=1)
        ruby_ring = Product(sku="AT-RUBY", name="Ruby Band", retail_price=20, sale_price=20, is_active=True)
        pearl_ring = Product(
            sku="AT-PEARL", name="Pearl Band", retail_price=20, sale_price=20, is_active=True
        )
        ruby_ring.attribute_links.append(ProductAttribute(attribute=metal, value="Rose gold-tone"))
        pearl_ring.attribute_links.append(ProductAttribute(attribute=metal, value="Silver-tone"))
        db.session.add_all([metal, ruby_ring, pearl_ring])
        db.session.commit()
        ids = ruby_ring.id, pearl_ring.id
    first = client.get(f"/catalog/product/{ids[0]}").get_data(as_text=True)
    second = client.get(f"/catalog/product/{ids[1]}").get_data(as_text=True)
    assert "<dt>Metal type</dt><dd>Rose gold-tone</dd>" in first
    assert "<dt>Metal type</dt><dd>Silver-tone</dd>" in second
    assert "Ruby Band" in client.get("/catalog/search?q=rose gold-tone").get_data(as_text=True)


def test_one_value_per_product_per_attribute(app):
    import pytest
    from sqlalchemy.exc import IntegrityError

    with app.app_context():
        finish = Attribute(name="Plating")
        product = Product(sku="AT-DUP", name="Dup", retail_price=1, sale_price=1)
        product.attribute_links = [
            ProductAttribute(attribute=finish, value="A"),
            ProductAttribute(attribute=finish, value="B"),
        ]
        db.session.add(product)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_admin_edits_details_inside_the_product_form(app, client):
    with app.app_context():
        clasp = Attribute(name="Closure")
        product = Product(sku="AT-ADMIN", name="Admin Bangle", retail_price=30, sale_price=30, is_active=True)
        db.session.add_all([clasp, product])
        db.session.commit()
        pid, clasp_id = product.id, clasp.id
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    page = client.get(f"/admin/product/edit/?id={pid}").get_data(as_text=True)
    assert "Details" in page
    data = {
        "sku": "AT-ADMIN",
        "name": "Admin Bangle",
        "retail_price": "30",
        "sale_price": "30",
        "is_active": "y",
        "attribute_links-0-attribute": str(clasp_id),
        "attribute_links-0-value": "Screw clasp",
    }
    assert client.post(f"/admin/product/edit/?id={pid}", data=data).status_code == 302
    with app.app_context():
        [link] = db.session.get(Product, pid).attribute_links
        assert (link.attribute.name, link.value) == ("Closure", "Screw clasp")
    types = client.get("/admin/attribute/").get_data(as_text=True)
    assert "Closure" in types and re.search(r"Products using it", types)
    assert client.get("/admin/productattribute/").status_code == 404  # folded into the product form
