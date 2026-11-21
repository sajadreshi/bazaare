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
    assert "This list is the shop menu" in html
    assert "<strong>Earrings</strong>" in html
    assert re.search(r"└─ Jhumkas", html)
    assert (
        html.index("<strong>Earrings</strong>")
        < html.index("└─ Jhumkas")
        < html.index("<strong>Neckpieces</strong>")
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
