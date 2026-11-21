from flask import abort, flash, jsonify, redirect, render_template, request, url_for

from app.catalog import catalog
from app.services import cart as cart_service
from app.services import catalog as catalog_service
from app.services import wishlist as wishlist_service


@catalog.route("/collection", methods=["GET"])
def collection():
    # The old "Our Collection" page now lives in the menu as Collections.
    return redirect(url_for("catalog.category", slug="collections"), code=301)


@catalog.route("/product/<int:productId>", methods=["GET", "POST"])
def product(productId):
    cart = None
    if request.method == "POST":
        # Related-product cards post their own product id as "pid".
        pid = request.form.get("pid", type=int) or productId
        try:
            cart_service.add_item(pid, request.form.get("size", type=int))
        except cart_service.CartError as error:
            flash(str(error))
            return redirect(url_for("catalog.product", productId=productId))
        cart = cart_service.get_cart()
    product = catalog_service.get_product(productId)
    xsells = catalog_service.cross_sells(product) if product else []
    return render_template(
        "catalog/product.html",
        product=product,
        images=catalog_service.product_images(product) if product else [],
        options=catalog_service.variant_options(product) if product else [],
        upsells=catalog_service.upsells(product) if product else [],
        xsells=xsells,
        similar=[] if xsells or not product else catalog_service.similar(product),
        cart=cart,
    )


@catalog.route("/c/<slug>")
def category(slug):
    category = catalog_service.get_category(slug)
    if category is None:
        abort(404)
    sort = request.args.get("sort", "featured")
    if sort not in catalog_service.SORTS:
        sort = "featured"
    return render_template(
        "catalog/category.html",
        category=category,
        parent=category.parent,
        siblings=[c for c in (category.parent or category).children if c.is_active and c.show_in_menu],
        products=catalog_service.category_products(category, sort),
        sort=sort,
        sorts=catalog_service.SORTS,
    )


@catalog.route("/search")
def search():
    query = request.args.get("q", "").strip()[:100]
    return render_template("catalog/search.html", query=query, products=catalog_service.search(query))


@catalog.route("/wishlist")
def wishlist():
    return render_template("catalog/wishlist.html", products=wishlist_service.products())


@catalog.route("/wishlist/<int:productId>", methods=["POST"])
def toggle_wishlist(productId):
    added = wishlist_service.toggle(productId)
    if request.accept_mimetypes.best == "application/json":
        return jsonify(added=added, count=len(wishlist_service.ids()))
    flash("Added to your wishlist." if added else "Removed from your wishlist.")
    back = request.referrer
    return redirect(back if back and back.startswith(request.host_url) else url_for("catalog.wishlist"))
