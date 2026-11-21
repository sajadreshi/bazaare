from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.customer import customer
from app.customer.addressHelper import (
    getCurrentBillingAddress,
    getCurrentShippingAddress,
    updateBillingAddress,
    updateShippingAddress,
)
from app.customer.customerUtil import findCurrentCustomer, updatePassword
from app.customer.forms import (
    BillingForm,
    ChangePassword,
    ProfileForm,
    ShippingForm,
    populateBillingAddressForm,
    populateProfileForm,
    populateshippingAddressForm,
)
from app.customer.profileHelper import getCurrentUserProfile, updateProfile
from app.services.orders import get_customer_order, list_customer_orders


@customer.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    # Check if user is loggedin
    proForm = ProfileForm()
    display = "profile"
    if current_user.is_authenticated:
        if request.method == "POST":
            if proForm.validate_on_submit():
                user = updateProfile(proForm)
                if user is not None:
                    flash("Profile updated successfully")
                    return redirect(request.referrer)
            else:
                display = "form"

        user = getCurrentUserProfile()
        proForm = populateProfileForm(proForm, user)
        return render_template(
            "customer/customer.html", page="profile", proform=proForm, user=user, display=display
        )
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))


@customer.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    billingForm = BillingForm()
    display = "billing"
    if current_user.is_authenticated:
        if request.method == "POST":
            if billingForm.validate_on_submit():
                billing = updateBillingAddress(billingForm)
                if billing is not None:
                    flash("Billing address updated successfully")
                    return redirect(request.referrer)
            else:
                display = "form"

        billingAddress = getCurrentBillingAddress()
        if not billingAddress:
            display = "form"
        billingForm = populateBillingAddressForm(billingForm, billingAddress)
        return render_template(
            "customer/customer.html",
            page="billingAddress",
            billingForm=billingForm,
            billingAddress=billingAddress,
            display=display,
        )
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))


@customer.route("/shipping", methods=["GET", "POST"])
@login_required
def shipping():
    shippingForm = ShippingForm()
    display = "shipping"
    if current_user.is_authenticated:
        if request.method == "POST":
            if shippingForm.validate_on_submit():
                shipping = updateShippingAddress(shippingForm)
                if shipping is not None:
                    flash("Shipping address updated successfully")
                    return redirect(request.referrer)
            else:
                display = "form"

        shippingAddress = getCurrentShippingAddress()
        if not shippingAddress:
            display = "form"
        shippingForm = populateshippingAddressForm(shippingForm, shippingAddress)
        return render_template(
            "customer/customer.html",
            page="shippingAddress",
            shippingForm=shippingForm,
            shippingAddress=shippingAddress,
            display=display,
        )
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))


@customer.route("/security", methods=["GET", "POST"])
@login_required
def security():
    passwordForm = ChangePassword()
    if current_user.is_authenticated:
        if request.method == "POST":
            if passwordForm.validate_on_submit():
                user = updatePassword(passwordForm)
                if user is not None:
                    flash("Password changed successfully")
                    return redirect(request.referrer)
                else:
                    flash("Error occured while changing")
                    return redirect(request.referrer)
        return render_template("customer/customer.html", page="changePassword", passwordForm=passwordForm)
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))


@customer.route("/orders")
@login_required
def orders():
    customer = findCurrentCustomer()
    orders = list_customer_orders(customer.id) if customer else []
    return render_template("customer/customer.html", page="orders", orders=orders)


@customer.route("/orderDetails/<int:orderId>")
@login_required
def orderDetails(orderId):
    customer = findCurrentCustomer()
    order = get_customer_order(orderId, customer.id if customer else None)
    if order is None:
        abort(404)
    return render_template("customer/customer.html", page="ordersDetails", order=order)
