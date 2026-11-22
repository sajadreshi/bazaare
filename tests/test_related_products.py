"""Related products: cross-sells ("Complete the look"), upsells ("Upgrade to"), fallbacks and admin."""

from decimal import Decimal

import pytest

from app.extension import db
from app.models import Category, Product, ProductAssociation, Variant
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login


def make(sku, name, price, code="NECK-NECKLACES"):
    product = Product(
        sku=sku, name=name, compare_at_price=Decimal(price), price=Decimal(price), is_active=True
    )
    product.categories = [Category.query.filter_by(code=code).one()]
    product.options = [Variant(stock=1000, name="One Size", is_default=True)]
    db.session.add(product)
    db.session.flush()
    return product


@pytest.fixture(scope="module")
def shop(app):
    with app.app_context():
        pendant = make("RP-PEND", "Lotus Pendant", "29")
        upgrade = make("RP-SET", "Lotus Necklace Set", "64")
        earrings = make("RP-EAR", "Lotus Jhumkas", "32", "EAR-JHUMKAS")
        ring = make("RP-RING", "Lotus Ring", "22", "ACC-RINGS")
        hidden = make("RP-HIDE", "Retired Lotus Cuff", "40", "ACC-BANGLES")
        hidden.is_active = False
        sibling = make("RP-SIB", "Sun Pendant", "31")
        pendant.associations = [
            ProductAssociation(target_product_id=ring.id, association_type="XSELL", position=2),
            ProductAssociation(target_product_id=earrings.id, association_type="XSELL", position=1),
            ProductAssociation(target_product_id=hidden.id, association_type="XSELL", position=0),
            ProductAssociation(target_product_id=upgrade.id, association_type="UPSELL", position=0),
        ]
        db.session.commit()
        return {p.sku: p.id for p in (pendant, upgrade, earrings, ring, hidden, sibling)}


def test_product_page_shows_upsells_and_cross_sells_in_order(client, shop):
    html = client.get(f"/catalog/product/{shop['RP-PEND']}").get_data(as_text=True)
    upsell_box = html[html.index('aria-label="Upgrade to"') :]
    assert "Lotus Necklace Set" in upsell_box[: upsell_box.index("</aside>")]
    look = html[html.index("Complete the look") :]
    assert look.index("Lotus Jhumkas") < look.index("Lotus Ring")  # position order
    assert "Retired Lotus Cuff" not in html  # inactive products are never suggested


def test_without_cross_sells_the_page_suggests_more_from_the_category(client, shop):
    html = client.get(f"/catalog/product/{shop['RP-SIB']}").get_data(as_text=True)
    assert "More necklaces" in html and "Lotus Pendant" in html
    assert "Complete the look" not in html and 'aria-label="Upgrade to"' not in html


def test_bag_suggests_cross_sells_not_already_in_the_bag(app, client, shop):
    client.post(f"/catalog/product/{shop['RP-PEND']}", data={"pid": shop["RP-PEND"]})
    client.post(f"/catalog/product/{shop['RP-RING']}", data={"pid": shop["RP-RING"]})
    html = client.get("/checkout/shopcart").get_data(as_text=True)
    suggestions = html[html.index("Complete the look") :]
    assert "Lotus Jhumkas" in suggestions
    assert "Lotus Ring" not in suggestions  # already in the bag


def test_one_link_per_product_pair_and_type(app, shop):
    from sqlalchemy.exc import IntegrityError

    with app.app_context():
        db.session.add(
            ProductAssociation(
                source_product_id=shop["RP-PEND"], target_product_id=shop["RP-RING"], association_type="XSELL"
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_deleting_a_product_removes_links_to_it(app, shop):
    with app.app_context():
        doomed = make("RP-DOOM", "Doomed Charm", "10", "ACC-RINGS")
        sibling = db.session.get(Product, shop["RP-SIB"])
        sibling.associations.append(ProductAssociation(target_product=doomed, association_type="XSELL"))
        db.session.commit()
        db.session.delete(doomed)
        db.session.commit()
        assert not db.session.get(Product, shop["RP-SIB"]).associations


def test_admin_product_form_edits_related_products_inline(app, client, shop):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    page = client.get(f"/admin/product/edit/?id={shop['RP-SIB']}").get_data(as_text=True)
    assert "Related products" in page and "Cross-sell: Complete the look" in page
    data = {
        "sku": "RP-SIB",
        "name": "Sun Pendant",
        "compare_at_price": "31",
        "price": "31",
        "is_active": "y",
        "associations-0-target_product": str(shop["RP-SET"]),
        "associations-0-association_type": "UPSELL",
        "associations-0-position": "0",
        "associations-0-is_active": "y",
    }
    assert client.post(f"/admin/product/edit/?id={shop['RP-SIB']}", data=data).status_code == 302
    with app.app_context():
        [link] = db.session.get(Product, shop["RP-SIB"]).associations
        assert (link.target_product.sku, link.association_type) == ("RP-SET", "UPSELL")
    assert "Lotus Necklace Set" in client.get(f"/catalog/product/{shop['RP-SIB']}").get_data(as_text=True)


def test_admin_association_list_uses_friendly_names(client, shop):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/productassociation/").get_data(as_text=True)
    assert "On the page of" in html and "Upsell: Upgrade to" in html
