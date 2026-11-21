from app.customer import customer
from flask_login import login_required, current_user
from flask import render_template, request, redirect, url_for, session, flash
from app.customer.forms import ProfileForm, populateProfileForm, BillingForm, populateBillingAddressForm, ShippingForm, populateshippingAddressForm, ChangePassword
from app.models import User
from app.customer.profileHelper import updateProfile, getCurrentUserProfile
from app.customer.addressHelper import updateBillingAddress, getCurrentBillingAddress, updateShippingAddress , getCurrentShippingAddress
from app.customer.customerUtil import updatePassword,fetchOrdersForCustomer
from app.checkout.confirmationHelper import get_cart

@customer.route("/profile",methods=["GET","POST"])

def profile():
    # Check if user is loggedin
    proForm = ProfileForm()
    display= 'profile'
    if current_user.is_authenticated:
        if request.method == 'POST':
            if proForm.validate_on_submit():
                user = updateProfile(proForm)
                if user is not None:
                    flash('Profile updated successfully')
                    return redirect(request.referrer)
            else:
                display = 'form'
                               
        user=getCurrentUserProfile()
        proForm = populateProfileForm(proForm,user)
        return render_template("customer/customer.html",page='profile',proform=proForm,user=user,display=display)
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))


@customer.route("/billing",methods=["GET","POST"])
def billing():
    billingForm = BillingForm()
    display= 'billing'
    if current_user.is_authenticated:
        if request.method == 'POST':
            if billingForm.validate_on_submit():
                billing = updateBillingAddress(billingForm)
                if billing is not None:
                    flash('Billing address updated successfully')
                    return redirect(request.referrer)
            else:
                display = 'form'
                               
        billingAddress=getCurrentBillingAddress()
        if not billingAddress:
           display = 'form'
        billingForm = populateBillingAddressForm(billingForm,billingAddress)
        return render_template("customer/customer.html",page='billingAddress',billingForm=billingForm,billingAddress=billingAddress,display=display)
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))

@customer.route("/shipping",methods=["GET","POST"])

def shipping():
    shippingForm = ShippingForm()
    display= 'shipping'
    if current_user.is_authenticated:
        if request.method == 'POST':
            if shippingForm.validate_on_submit():
                shipping = updateShippingAddress(shippingForm)
                if shipping is not None:
                    flash('Shipping address updated successfully')
                    return redirect(request.referrer)
            else:
                display = 'form'
                               
        shippingAddress=getCurrentShippingAddress()
        if not shippingAddress:
           display = 'form'
        shippingForm = populateshippingAddressForm(shippingForm,shippingAddress)
        return render_template("customer/customer.html",page='shippingAddress',shippingForm=shippingForm,shippingAddress=shippingAddress,display=display)
      # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))

@customer.route("/security",methods=["GET","POST"])
@login_required
def security():
    passwordForm = ChangePassword()
    if current_user.is_authenticated:
        if request.method == 'POST':
            if passwordForm.validate_on_submit():
                user = updatePassword(passwordForm)
                if user is not None:
                    flash('Password changed successfully')
                    return redirect(request.referrer)
                else:
                    flash('Error occured while changing')
                    return redirect(request.referrer)
        return render_template("customer/customer.html",page='changePassword',passwordForm=passwordForm)
      # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))

@customer.route("/orders",methods=["GET","POST"])
@login_required
def orders():
    # Check if user is loggedin
    if current_user.is_authenticated:
        orders = fetchOrdersForCustomer()
        return render_template("customer/customer.html",page='orders', orders=orders)
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))

@customer.route("/orderDetails/<orderId>",methods=["GET","POST"])
@login_required
def orderDetails(orderId):
    if current_user.is_authenticated:
      
      if orderId:
       order = get_cart(orderId) 
       return render_template("customer/customer.html",page='ordersDetails',  cart=order)
    # User is not loggedin redirect to login page
    return redirect(url_for("auth.login"))