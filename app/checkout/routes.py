import logging

from flask import abort, flash, redirect, render_template, request, url_for

from app.checkout import checkout
from app.checkout.addressHelper import save_billing_address, save_shipping_address
from app.checkout.checkoutHelper import fetchSizeForProduct, updateVariantSize
from app.checkout.confirmationHelper import get_cart
from app.checkout.deliveryDateHelper import saveDeliveryDate
from app.checkout.forms import (
    BillingForm,
    DeliveryDateForm,
    PlaceOrderForm,
    ShippingForm,
    prepopulateBillingForm,
    prepopulateDeliveryForm,
    prepopulateShippingForm,
)
from app.checkout.getcarthelper import get_current_cart
from app.checkout.placeOrderHelper import placeOrder
from app.checkout.removeitem import delete_item

log = logging.getLogger(__name__)


def back(fragment=""):
    """Redirect to the page the form was posted from (or the cart if unknown)."""
    return redirect((request.referrer or url_for("checkout.shopcart")) + fragment)


@checkout.route("/remove/<int:itemId>", methods=["POST"])
def remove(itemId):
    delete_item(itemId)
    return back()


@checkout.route("/shopcart", methods=["GET", "POST"])
def shopcart():
    if request.method == "POST":
        new_size = request.form.get("size", type=int)
        product_id = request.form.get("productId", type=int)
        item_id = request.form.get("itemId", type=int)
        updateVariantSize(item_id, new_size, product_id)
    cur_cart = get_current_cart()
    return render_template("checkout/shopcart.html", cart=cur_cart)


@checkout.route("/order", methods=["GET", "POST"])
def order():
    shipping_form = ShippingForm()
    billing_form = BillingForm()
    delivery_form = DeliveryDateForm()
    place_order_form = PlaceOrderForm()

    if request.method == "POST":
        formId = request.form.get("form_id", "")
        if formId == "shipping_form":
            if shipping_form.validate_on_submit():
                save_shipping_address(shipping_form)
                return back()
        elif formId == "billing_form":
            if billing_form.validate_on_submit():
                save_billing_address(billing_form)
                return back()
        elif formId == "delivery_form":
            if delivery_form.validate_on_submit():
                saveDeliveryDate(delivery_form)
                return back("#collapseFour")
        elif formId == "place_order_form":
            if place_order_form.validate_on_submit():
                status = placeOrder(place_order_form)
                if not status.isSuccess:
                    flash(status.error)
                    return back()
                else:
                    return redirect(url_for("checkout.confirm", cartId=status.cartId))
    cur_cart = get_current_cart()
    shipping_form = prepopulateShippingForm(cur_cart, shipping_form)
    billing_form = prepopulateBillingForm(cur_cart, billing_form)
    delivery_form = prepopulateDeliveryForm(cur_cart, delivery_form)
    return render_template(
        "checkout/checkout.html",
        cart=cur_cart,
        shipping_form=shipping_form,
        billing_form=billing_form,
        delivery_form=delivery_form,
        place_order_form=place_order_form,
    )


@checkout.route("/confirm/<int:cartId>")
def confirm(cartId):
    # get_cart only returns carts owned by the current customer.
    cart = get_cart(cartId)
    if not cart:
        abort(404)
    return render_template("checkout/confirmation.html", cart=cart)


@checkout.route("/size/<int:productId>")
def size(productId):
    return fetchSizeForProduct(productId)
