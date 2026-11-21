from flask import flash, redirect, render_template, request, url_for

from app.catalog import catalog
from app.services import cart as cart_service
from app.services import catalog as catalog_service


@catalog.route("/collection", methods=["GET"])
def collection():
    return render_template("catalog/collection.html", shelves=catalog_service.collection_shelves())


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
    return render_template(
        "catalog/product.html",
        product=product,
        images=catalog_service.product_images(product) if product else [],
        options=catalog_service.variant_options(product) if product else [],
        xsells=catalog_service.cross_sells(product) if product else [],
        cart=cart,
    )
