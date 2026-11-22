from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.auth import bp
from app.auth.resetPassword import send_password_reset_email
from app.extension import db
from app.models import User
from app.services.account import sign_in, sign_out
from app.services.customers import get_or_create_user_customer
from app.urls import is_safe_next

from .forms import LoginForm, RegistrationForm, ResetPasswordForm, ResetPasswordRequestForm


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("That email and password don't match an account. Please try again.")
            return redirect(url_for("auth.login", next=request.args.get("next")))
        sign_in(user, remember=form.remember_me.data)
        next_page = request.args.get("next")
        if not is_safe_next(next_page):
            next_page = url_for("main.home")
        return redirect(next_page)

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    sign_out()
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(first_name=form.first_name.data, last_name=form.last_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        db.session.commit()
        get_or_create_user_customer(user)
        db.session.commit()
        sign_in(user)  # keeps anything already in their bag
        flash(f"Welcome to BazaarE', {user.first_name}! Your account is ready.")
        next_page = request.args.get("next")
        return redirect(next_page if is_safe_next(next_page) else url_for("customer.profile"))
    return render_template("auth/register.html", title="Register", form=form)


@bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash("If there's an account for that email, we've sent a link to reset the password.")
        return redirect(url_for("auth.login"))
    return render_template("auth/resetPasswordRequest.html", title="Reset Password", form=form)


@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("main.home"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been changed. Please sign in.")
        return redirect(url_for("auth.login"))
    return render_template("auth/resetPassword.html", form=form)
