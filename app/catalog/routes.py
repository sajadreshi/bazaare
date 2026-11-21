from flask import flash, redirect, render_template, request, url_for

from app.catalog import catalog
from app.catalog.collectionbuilder import build_collection
from app.catalog.productbuilder import build_crossells, build_product
from app.services import cart as cart_service


@catalog.route("/collection", methods=["GET"])
def collection():
    collection = build_collection()
    return render_template("catalog/collection.html", collection=collection)


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
    product = build_product(productId)
    xsells = build_crossells(productId)
    return render_template("catalog/product.html", product=product, xsells=xsells, cart=cart)
