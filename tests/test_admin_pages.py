"""Every admin screen's list and create pages load (catches crashes like an un-loadable list column)."""

import pytest

from app.extension import admin
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.test_security import login


def model_views():
    return [view for view in admin._views if hasattr(view, "model")]


@pytest.fixture
def admin_client(client):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return client


def test_every_admin_list_and_create_page_loads(app, admin_client, product_ids):
    with app.app_context():
        views = model_views()
    assert len(views) >= 10
    for view in views:
        base = f"/admin/{view.endpoint}/"
        assert admin_client.get(base).status_code == 200, base
        if view.can_create:
            assert admin_client.get(base + "new/").status_code == 200, base + "new/"


def test_admin_menu_has_no_home_page_content(admin_client):
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "Home banner slides" in html
    assert "Home Page Content" not in html
