"""Who is shopping: the Customer row behind the browser session.

Guests get a random 10-digit customer id kept in the session. Registered
users' customer id is their user id (set on login).
"""

import secrets

from flask import session
from flask_login import current_user

from app.extension import db
from app.models import Customer

SESSION_KEY = "customer_id"


def _new_guest_id():
    # 10 digits, far above any user id, so guest and registered ids never collide.
    return 1_000_000_000 + secrets.randbelow(9_000_000_000)


def get_current_customer():
    """The current session's Customer, or None if it has none yet."""
    customer_id = session.get(SESSION_KEY)
    return db.session.get(Customer, customer_id) if customer_id else None


def get_or_create_current_customer():
    """The current session's Customer, creating a guest (or the user's) record if needed."""
    customer_id = session.get(SESSION_KEY)
    if not customer_id:
        customer_id = current_user.id if current_user.is_authenticated else _new_guest_id()
        session[SESSION_KEY] = customer_id
    customer = db.session.get(Customer, customer_id)
    if customer is None:
        registered = current_user.is_authenticated and current_user.id == customer_id
        customer = Customer(
            id=customer_id,
            customer_type="REGISTERED" if registered else "GUEST",
            user_id=current_user.id if registered else None,
        )
        db.session.add(customer)
        db.session.flush()
    return customer


def get_or_create_user_customer(user):
    """The Customer record for a registered user (id == user id)."""
    customer = db.session.get(Customer, user.id)
    if customer is None:
        customer = Customer(id=user.id, customer_type="REGISTERED", user_id=user.id)
        db.session.add(customer)
        db.session.flush()
    return customer
