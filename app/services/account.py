"""A signed-in shopper's account: profile, password and saved addresses."""

from app.extension import db
from app.services.customers import get_or_create_user_customer

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
