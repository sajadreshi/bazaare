import os

from flask import abort, current_app, render_template, send_from_directory

from app.extension import db
from app.main import main
from app.models import Page
from app.services import catalog


def _tiles(codes):
    """(category, image key) for each active category: its banner, else its first product's photo."""
    tiles = []
    for code in codes:
        category = catalog.get_category(code)
        if category is None:
            continue
        products = catalog.category_products(category)
        image = category.banner_image or next((p.main_image for p in products if p.main_image), None)
        tiles.append((category, image))
    return tiles


@main.route("/")
def home():
    collections = catalog.get_category("COLLECTIONS")
    return render_template(
        "main/home.html",
        home=catalog.home_page(),
        hero=collections,
        shop_by=_tiles(["EARRINGS", "NECKPIECES", "ACCESSORIES"]),
        new_arrivals=catalog.new_arrivals(8),
        bestsellers=catalog.products_in("BESTSELLERS", 8),
        crafts=_tiles([c.code for c in collections.children if c.is_active]) if collections else [],
        gifting=_tiles(["GIFT-UNDER-25", "GIFT-UNDER-50", "GIFT-SPECIAL"]),
    )


def _page(slug):
    page = db.session.query(Page).filter_by(slug=slug, is_published=True).first()
    if page is None:
        abort(404)
    others = (
        db.session.query(Page).filter(Page.is_published.is_(True)).order_by(Page.position, Page.title).all()
    )
    return render_template("main/page.html", page=page, pages=others)


@main.route("/favicon.ico")
def favicon():
    # Browsers ask for /favicon.ico directly (e.g. for bookmarks and PDFs of a page).
    return send_from_directory(
        os.path.join(current_app.static_folder, "images"), "favicon.ico", mimetype="image/vnd.microsoft.icon"
    )


@main.route("/about")
def about():
    return _page("about")


@main.route("/policies/<slug>")
def policy(slug):
    return _page(slug)
