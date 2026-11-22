from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.customer import customer
from app.customer.forms import BillingForm, ChangePassword, ProfileForm, ShippingForm
from app.services import account
from app.services.checkout import save_address
from app.services.customers import get_or_create_user_customer
from app.services.orders import get_customer_order, list_customer_orders


@customer.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        account.update_profile(current_user, form)
        flash("Your details are saved.")
        return redirect(url_for("customer.profile"))
    return render_template("customer/profile.html", page="profile", form=form.fill_from(current_user))


def _address_page(kind, form_class):
    form = form_class()
    if form.validate_on_submit():
        save_address(form, kind)
        flash(f"Your {kind} address is saved.")
        return redirect(url_for(f"customer.{kind}"))
    shipping, billing = account.saved_addresses(current_user)
    address = shipping if kind == "shipping" else billing
    form.fill_from(address)
    editing = form.is_submitted() or address is None or request.args.get("edit") is not None
    return render_template(
        "customer/addresses.html",
        page="addresses",
        kind=kind,
        form=form,
        address=address,
        shipping=shipping,
        billing=billing,
        editing=editing,
    )


@customer.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    return _address_page("billing", BillingForm)


@customer.route("/shipping", methods=["GET", "POST"])
@login_required
def shipping():
    return _address_page("shipping", ShippingForm)


@customer.route("/security", methods=["GET", "POST"])
@login_required
def security():
    form = ChangePassword()
    if form.validate_on_submit():
        if account.change_password(current_user, form.current_password.data, form.password.data):
            flash("Your password is changed.")
            return redirect(url_for("customer.security"))
        form.current_password.errors.append("That isn't your current password.")
    return render_template("customer/security.html", page="security", form=form)


@customer.route("/orders")
@login_required
def orders():
    customer = get_or_create_user_customer(current_user)
    return render_template("customer/orders.html", page="orders", orders=list_customer_orders(customer.id))


@customer.route("/orderDetails/<int:orderId>")
@login_required
def orderDetails(orderId):
    order = get_customer_order(orderId, get_or_create_user_customer(current_user).id)
    if order is None:
        abort(404)
    return render_template("customer/order.html", page="orders", order=order)
