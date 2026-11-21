"""Admin category list shown as the menu tree."""

import re

from app.adminapp.views import category_tree
from app.models import Category
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login


def test_category_tree_orders_parents_then_children(app):
    with app.app_context():
        tree = [(c.code, depth) for c, depth in category_tree(Category.query.all())]
    codes = [code for code, _ in tree]
    assert (
        codes.index("EARRINGS")
        < codes.index("EAR-JHUMKAS")
        < codes.index("EAR-CUFFS")
        < codes.index("NECKPIECES")
    )
    assert dict(tree)["EARRINGS"] == 0 and dict(tree)["EAR-JHUMKAS"] == 1
    top = [code for code, depth in tree if depth == 0]
    assert top[:8] == [
        "NEW",
        "COLLECTIONS",
        "EARRINGS",
        "NECKPIECES",
        "ACCESSORIES",
        "BESTSELLERS",
        "GIFTING",
        "SALE",
    ]


def test_admin_category_list_shows_the_tree(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/category/").get_data(as_text=True)
    assert "This is the shop menu" in html
    main = re.compile(r'bz-tree__name--0">Earrings<')
    assert main.search(html) and re.search(r'└</span><a [^>]*bz-tree__name--1">Jhumkas<', html)
    assert (
        html.index('bz-tree__name--0">Earrings<')
        < html.index('bz-tree__name--1">Jhumkas<')
        < html.index('bz-tree__name--0">Neckpieces<')
    )
    assert "≤ $25" in html  # price rule column


def test_admin_category_form_has_parent_position_and_banner_upload(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    html = client.get("/admin/category/new/").get_data(as_text=True)
    for field in [
        'name="parent"',
        'name="position"',
        'name="show_in_menu"',
        'name="max_price"',
        'type="file"',
    ]:
        assert field in html, field


def test_arrows_reorder_menu_items_and_sub_category_link_preselects_parent(app, client):
    from app.extension import db
    from app.models import Category

    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    with app.app_context():
        top = Category.query.filter(Category.parent_id.is_(None), Category.show_in_menu.is_(True))
        names = [c.name for c in sorted(top, key=lambda c: (c.position, c.name.lower()))]
        second = Category.query.filter_by(name=names[1]).one().id
        earrings = Category.query.filter_by(code="EARRINGS").one().id
    assert client.post(f"/admin/category/move/{second}/up").status_code == 302
    with app.app_context():
        top = Category.query.filter(Category.parent_id.is_(None), Category.show_in_menu.is_(True))
        now = [c.name for c in sorted(top, key=lambda c: (c.position, c.name.lower()))]
        assert now[:2] == [names[1], names[0]] and now[2:] == names[2:]
        client.post(f"/admin/category/move/{second}/down")
        db.session.expire_all()
    html = client.get(f"/admin/category/new/?parent={earrings}").get_data(as_text=True)
    assert re.search(rf'<option selected value="{earrings}">Earrings</option>', html)
    html = client.get(f"/admin/category/edit/?id={earrings}").get_data(as_text=True)
    assert "View in shop" in html and "Jhumkas" in html and "/catalog/c/<strong>earrings</strong>" in html
