from flask import render_template

from app.main import main
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


@main.route("/about")
def about():
    return render_template("main/about.html")
