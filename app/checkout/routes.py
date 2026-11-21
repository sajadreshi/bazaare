from flask import abort, flash, jsonify, redirect, render_template, request, url_for

from app.checkout import checkout
from app.checkout.forms import BillingForm, DeliveryDateForm, PlaceOrderForm, ShippingForm
from app.services import cart as cart_service
from app.services import catalog as catalog_service
from app.services import checkout as checkout_service
from app.services.customers import get_current_customer
from app.services.orders import get_customer_order


def back(fragment=""):
    """Redirect to the page the form was posted from (or the cart if unknown)."""
    return redirect((request.referrer or url_for("checkout.shopcart")) + fragment)


@checkout.route("/remove/<int:itemId>", methods=["POST"])
def remove(itemId):
    cart_service.remove_item(itemId)
    return back()


@checkout.route("/shopcart", methods=["GET", "POST"])
def shopcart():
    if request.method == "POST":
        cart_service.change_variant(request.form.get("itemId", type=int), request.form.get("size", type=int))
    cart = cart_service.get_cart()
    return render_template(
        "checkout/shopcart.html", cart=cart, suggestions=catalog_service.bag_suggestions(cart)
    )


@checkout.route("/order", methods=["GET", "POST"])
def order():
    shipping_form = ShippingForm()
    billing_form = BillingForm()
    delivery_form = DeliveryDateForm()
    place_order_form = PlaceOrderForm()

    if request.method == "POST":
        form_id = request.form.get("form_id", "")
        if form_id == "shipping_form" and shipping_form.validate_on_submit():
            checkout_service.save_address(shipping_form, "shipping")
            return back()
        if form_id == "billing_form" and billing_form.validate_on_submit():
            checkout_service.save_address(billing_form, "billing")
            return back()
        if form_id == "delivery_form" and delivery_form.validate_on_submit():
            if not checkout_service.save_delivery(
                delivery_form.delivery_date.data, delivery_form.delivery_window.data
            ):
                flash("Please choose one of the delivery dates and windows offered.")
            return back("#collapseFour")
        if form_id == "place_order_form" and place_order_form.validate_on_submit():
            result = checkout_service.place_order(place_order_form.payment_method.data)
            if not result.ok:
                flash(result.error)
                return back()
            return redirect(url_for("checkout.confirm", orderId=result.order.id))

    cart = cart_service.get_cart()
    customer = cart.customer if cart else None
    shipping_form.fill_from(customer.shipping_address if customer else None)
    billing_form.fill_from(customer.billing_address if customer else None)
    delivery_form.fill_from(cart)
    return render_template(
        "checkout/checkout.html",
        cart=cart,
        status=checkout_service.checkout_status(cart),
        shipping_form=shipping_form,
        billing_form=billing_form,
        delivery_form=delivery_form,
        place_order_form=place_order_form,
    )


@checkout.route("/confirm/<int:orderId>")
def confirm(orderId):
    customer = get_current_customer()
    order = get_customer_order(orderId, customer.id if customer else None)
    if order is None:
        abort(404)
    return render_template("checkout/confirmation.html", order=order)


@checkout.route("/size/<int:productId>")
def size(productId):
    return jsonify(cart_service.variant_choices(productId))
