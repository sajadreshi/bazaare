"""A signed-in shopper's account: profile, password and saved addresses."""

from flask import session
from flask_login import login_user, logout_user

from app.extension import db
from app.services.cart import adopt_guest_cart
from app.services.customers import SESSION_KEY, get_or_create_user_customer

PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "cell_number",
    "marketing_email",
    "transactional_email",
    "marketing_sms",
    "transactional_sms",
)
MIN_PASSWORD_LENGTH = 8


def is_admin(user):
    return bool(user and user.is_authenticated and any(r.name.lower() == "admin" for r in user.roles))


def sign_in(user, remember=False):
    """Log a user in, switch the session to their customer record and keep their guest cart."""
    guest_customer_id = session.get(SESSION_KEY)
    login_user(user, remember=remember)
    customer = get_or_create_user_customer(user)
    session[SESSION_KEY] = customer.id
    adopt_guest_cart(guest_customer_id, customer)  # commits


def sign_out():
    logout_user()
    session.pop(SESSION_KEY, None)


def update_profile(user, form):
    for field in PROFILE_FIELDS:
        setattr(user, field, getattr(form, field).data)
    db.session.commit()
    return user


def change_password(user, current_password, new_password):
    """Set a new password after re-checking the current one. Returns False if it was wrong."""
    if not user.check_password(current_password):
        return False
    user.set_password(new_password)
    db.session.commit()
    return True


def saved_addresses(user):
    """(shipping, billing) Address rows for the user's account (either may be None)."""
    customer = get_or_create_user_customer(user)
    return customer.shipping_address, customer.billing_address
