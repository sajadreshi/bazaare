from werkzeug.urls import url_parse
from flask import render_template, request, redirect, url_for, session, flash, Blueprint
from flask_login import login_required, login_user, logout_user, current_user
from app import db
from app.models import User, Customer
from .forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.auth import bp
from app.auth.resetPassword import send_password_reset_email





@bp.route("/login", methods=["GET", "POST"])
def login():
     
    cust_id = session.get('customer_id') if 'customer_id' in session  else 'nothing'
    print('cust_id   '+str(cust_id))
    if current_user.is_authenticated:
       return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        session['customer_id'] = current_user.id
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.home')
        return redirect(next_page)
      
    return render_template("auth/login.html", form=form)

@bp.route("/logout")
def logout():
    # Remove session data, this will log the user out
    if current_user.is_authenticated:
       logout_user()
       session.pop('customer_id')
    # Redirect to login page
    return redirect(url_for("auth.login"))

@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        db.session.commit()
        createCustomerEntry(user)
        flash('You have successfully registered. Pleaser login here')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return  redirect(url_for('main.home'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))
    return render_template('auth/resetPasswordRequest.html',
                           title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return  redirect(url_for('main.home'))
    user = User.verify_reset_password_token(token)
    if not user:
        return  redirect(url_for('main.home'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for("auth.login"))
    return render_template('auth/resetPassword.html', form=form)

def createCustomerEntry(user):
    customer = Customer(id=user.id,customer_type='REGISTERED',user_id=user.id)
    db.session.add(customer)
    db.session.commit()
