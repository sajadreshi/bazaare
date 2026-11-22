"""Coupon codes: checking a code, working out its discount, and counting its uses.

A coupon takes a percentage or a fixed amount off the merchandise. The discount is
spread over the bag's lines (so sales tax is charged on the discounted prices) and
free standard shipping is judged on the bag after the discount.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.extension import db
from app.models import Coupon, utcnow

CENT = Decimal("0.01")


def normalise(code):
    return "".join((code or "").split()).upper()[:40]


def find(code):
    code = normalise(code)
    return db.session.query(Coupon).filter(Coupon.code == code).first() if code else None


def problem(coupon, merchandise, now=None):
    """Why this coupon can't be used on a bag worth ``merchandise`` right now, or None."""
    now = now or utcnow()
    if coupon is None or not coupon.is_active:
        return "That code isn't valid."
    if coupon.starts_at and now < coupon.starts_at:
        return f"{coupon.code} starts on {coupon.starts_at:%d %b %Y}."
    if coupon.ends_at and now > coupon.ends_at:
        return f"{coupon.code} has expired."
    if coupon.max_uses is not None and coupon.times_used >= coupon.max_uses:
        return f"{coupon.code} has been fully used."
    if coupon.min_order and merchandise < coupon.min_order:
        short = coupon.min_order - merchandise
        return f"{coupon.code} needs a bag of ${coupon.min_order:.2f} or more (add ${short:.2f})."
    return None


def discount(coupon, merchandise):
    """The money off a bag worth ``merchandise`` (never more than the bag)."""
    if coupon is None:
        return Decimal("0.00")
    if coupon.kind == "PERCENT":
        amount = Decimal(merchandise) * Decimal(coupon.value) / 100
    else:
        amount = Decimal(coupon.value)
    return min(amount, Decimal(merchandise)).quantize(CENT, rounding=ROUND_HALF_UP)


def apply_code(cart, code):
    """Attach a coupon to the cart. Returns (ok, message)."""
    coupon = find(code)
    if coupon is None:
        return False, "That code isn't valid."
    merchandise = sum((Decimal(i.product_price or 0) for i in cart.pending_items), Decimal(0))
    reason = problem(coupon, merchandise)
    if reason:
        return False, reason
    cart.coupon = coupon
    return True, f"{coupon.code} applied: {coupon.offer}."


def redeem(cart):
    """At order time: re-check the cart's coupon and count a use (row locked). Returns an error or None."""
    if cart.coupon_id is None:
        return None
    coupon = (
        db.session.query(Coupon)
        .filter(Coupon.id == cart.coupon_id)
        .with_for_update()
        .populate_existing()
        .one()
    )
    reason = problem(coupon, cart.total_merchandise or 0)
    if reason:
        return f"Your coupon can't be used: {reason}"
    coupon.times_used += 1
    return None
