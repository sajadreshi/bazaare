from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from app.checkout import checkout
from app.checkout.forms import BillingForm, PlaceOrderForm, ShippingForm, ShippingMethodForm
from app.services import cart as cart_service
from app.services import catalog as catalog_service
from app.services import checkout as checkout_service
from app.services.customers import get_current_customer
from app.services.orders import get_customer_order
from app.services.shipping import DEFAULT_METHOD, METHODS


def back(fragment=""):
    """Redirect to the page the form was posted from (or the cart if unknown)."""
    return redirect((request.referrer or url_for("checkout.shopcart")) + fragment)


def free_shipping_gap(cart):
    """How much more to spend for free standard shipping (None when it's already free or not offered)."""
    if cart is None or not cart.pending_items:
        return None
    standard = METHODS[DEFAULT_METHOD]
    merchandise = cart.total_merchandise or 0
    if standard.free_over is None or merchandise >= standard.free_over:
        return None
    return standard.free_over - merchandise


STEPS = ("shipping", "billing")


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
        "checkout/shopcart.html",
        cart=cart,
        suggestions=catalog_service.bag_suggestions(cart),
        free_shipping_gap=free_shipping_gap(cart),
        free_over=METHODS[DEFAULT_METHOD].free_over,
    )


@checkout.route("/order", methods=["GET", "POST"])
def order():
    shipping_form = ShippingForm()
    billing_form = BillingForm()
    delivery_form = ShippingMethodForm()
    place_order_form = PlaceOrderForm()

    failed = None  # the step whose form had errors stays open
    if request.method == "POST":
        form_id = request.form.get("form_id", "")
        if form_id == "shipping_form":
            if shipping_form.validate_on_submit():
                checkout_service.save_address(shipping_form, "shipping")
                return redirect(url_for("checkout.order"))
            failed = "shipping"
        if form_id == "billing_form":
            if billing_form.validate_on_submit():
                checkout_service.save_address(billing_form, "billing")
                return redirect(url_for("checkout.order"))
            failed = "billing"
        if form_id == "billing_same" and FlaskForm().validate_on_submit():  # checks the CSRF token
            if not checkout_service.use_shipping_for_billing():
                flash("Please add your shipping address first.")
            return redirect(url_for("checkout.order"))
        if form_id == "shipping_method_form":
            delivery_form.fill_from(cart_service.get_cart())  # choices must exist before validating
            if delivery_form.validate_on_submit():
                if not checkout_service.save_shipping_method(delivery_form.shipping_method.data):
                    flash("Please choose one of the shipping methods offered.")
                return redirect(url_for("checkout.order") + "#delivery")
        if form_id == "place_order_form" and place_order_form.validate_on_submit():
            result = checkout_service.place_order(place_order_form.payment_method.data)
            if not result.ok:
                flash(result.error)
                return redirect(url_for("checkout.order"))
            return redirect(url_for("checkout.confirm", orderId=result.order.id))

    cart = cart_service.get_cart()
    customer = cart.customer if cart else None
    shipping_form.fill_from(customer.shipping_address if customer else None)
    if (
        current_user.is_authenticated
        and not shipping_form.is_submitted()
        and not shipping_form.first_name.data
    ):
        # First checkout for a signed-in shopper: start from their account details.
        shipping_form.first_name.data = current_user.first_name
        shipping_form.last_name.data = current_user.last_name
        shipping_form.email.data = current_user.email
        shipping_form.phone.data = current_user.cell_number
    billing_form.fill_from(customer.billing_address if customer else None)
    delivery_form.fill_from(cart)
    status = checkout_service.checkout_status(cart)
    done = {"shipping": status.shipping, "billing": status.billing}
    editing = request.args.get("edit")
    open_step = failed or (editing if editing in STEPS else None)
    open_step = open_step or next((step for step in STEPS if not done[step]), None)
    return render_template(
        "checkout/checkout.html",
        cart=cart,
        status=status,
        open_step=open_step,
        customer=customer,
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
