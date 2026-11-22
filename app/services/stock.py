"""Stock: counts go down when an order is placed and back up if it's cancelled.

Only stock above the shop's threshold can be sold (see services.inventory), and a
product that sells out is hidden from the shop until it's restocked. An option whose
``stock`` is empty (from before stock was required) isn't counted.
"""

from collections import Counter

from app.extension import db
from app.models import Variant
from app.services import inventory


class OutOfStock(Exception):
    """Raised while placing an order when an option no longer has enough stock."""


def take_for_cart(cart):
    """Lock and reduce stock for every tracked option in the cart. Runs in the caller's transaction."""
    wanted = Counter(item.size_id for item in cart.pending_items if item.size_id)
    if not wanted:
        return
    variants = (
        db.session.query(Variant)
        .filter(Variant.id.in_(wanted), Variant.stock.isnot(None))
        .order_by(Variant.id)
        .with_for_update()
        .populate_existing()
        .all()
    )
    for variant in variants:
        count = wanted[variant.id]
        if variant.available < count:
            left = f"only {variant.available} left" if variant.available > 0 else "it just sold out"
            name = f"{variant.product.name} ({variant.name})"
            raise OutOfStock(f"Sorry, {name}: {left}. Please update your bag.")
        variant.stock -= count
    inventory.refresh({variant.product for variant in variants})


def _order_counts(order):
    return Counter(line.variant_id for line in order.items if line.variant_id)


def put_back(order):
    """A cancelled order's items go back on the shelf."""
    counts = _order_counts(order)
    variants = db.session.query(Variant).filter(Variant.id.in_(counts), Variant.stock.isnot(None)).all()
    for variant in variants:
        variant.stock += counts[variant.id]
    inventory.refresh({variant.product for variant in variants})


def take_again(order):
    """A reopened order takes its items off the shelf again (never below zero)."""
    counts = _order_counts(order)
    variants = db.session.query(Variant).filter(Variant.id.in_(counts), Variant.stock.isnot(None)).all()
    for variant in variants:
        variant.stock = max(0, variant.stock - counts[variant.id])
    inventory.refresh({variant.product for variant in variants})
