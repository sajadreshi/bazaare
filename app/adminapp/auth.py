"""The admin's own sign-in page at /admin/login (separate from the shop's login)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import BooleanField, EmailField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

from app.models import User
from app.services.account import is_admin, sign_in, sign_out
from app.urls import is_safe_next

bp = Blueprint("admin_auth", __name__, url_prefix="/admin")

# One message for every failure, so the form doesn't reveal which emails exist
# or which accounts are shoppers rather than admins.
LOGIN_FAILED = "Incorrect email or password, or this account doesn't have admin access."


class AdminLoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Keep me signed in on this device")
    submit = SubmitField("Sign in")


def _admin_home(next_page=None):
    return redirect(
        next_page if is_safe_next(next_page) and next_page.startswith("/admin") else url_for("admin.index")
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_page = request.args.get("next")
    if is_admin(current_user):
        return _admin_home(next_page)
    form = AdminLoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        if user is None or not user.check_password(form.password.data) or not is_admin(user):
            flash(LOGIN_FAILED, "error")
            return render_template("admin/login.html", form=form), 401
        sign_in(user, remember=form.remember_me.data)
        return _admin_home(next_page)
    return render_template("admin/login.html", form=form)


@bp.route("/logout")
def logout():
    sign_out()
    flash("You have been signed out.", "info")
    return redirect(url_for("admin_auth.login"))
