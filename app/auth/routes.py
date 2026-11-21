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
            flash("Invalid username or password")
            return redirect(url_for("auth.login"))
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
        flash("You have successfully registered. Pleaser login here")
        return redirect(url_for("auth.login"))
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
        flash("Check your email for the instructions to reset your password")
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
        flash("Your password has been reset.")
        return redirect(url_for("auth.login"))
    return render_template("auth/resetPassword.html", form=form)
