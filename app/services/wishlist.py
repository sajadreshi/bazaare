"""A shopper's wishlist, kept in their session (no account needed)."""

from flask import session

from app.extension import db
from app.models import Product

SESSION_KEY = "wishlist"
MAX_ITEMS = 100


def ids():
    return [int(i) for i in session.get(SESSION_KEY, [])]


def contains(product_id):
    return product_id in ids()


def toggle(product_id):
    """Add or remove a product. Returns True if it is now in the wishlist."""
    current = ids()
    if product_id in current:
        current.remove(product_id)
        added = False
    else:
        if db.session.get(Product, product_id) is None:
            return False
        current = ([product_id] + current)[:MAX_ITEMS]
        added = True
    session[SESSION_KEY] = current
    return added


def products():
    wanted = ids()
    if not wanted:
        return []
    found = {
        p.id: p for p in db.session.query(Product).filter(Product.id.in_(wanted), Product.is_active.is_(True))
    }
    return [found[i] for i in wanted if i in found]
