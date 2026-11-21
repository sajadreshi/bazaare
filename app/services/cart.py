"""The shopping cart: adding, removing and re-sizing items, and keeping totals right.

A customer has at most one PENDING cart. Prices are computed here, from the
database, never taken from the browser.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.extension import db
from app.models import Cart, Item, Product, Variant
from app.services.customers import get_current_customer, get_or_create_current_customer
from app.services.shipping import method_for

log = logging.getLogger(__name__)

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class CartError(Exception):
    """A cart action the shopper can fix (shown to them as a message)."""


def _money(value):
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def line_price(product, variant):
    """Price of one item: the product's sale price times the variant's multiplier."""
    multiplier = Decimal(str(variant.quantity)) if variant and variant.quantity is not None else Decimal(1)
    return _money(Decimal(str(product.sale_price or 0)) * multiplier)


def product_variants(product):
    return product.variant.order_by(Variant.id).all()


def default_variant(variants):
    return next((v for v in variants if v.is_default), variants[0] if variants else None)


def variant_choices(product_id):
    """[[id, size, description], ...] for the cart's "change size" dropdown."""
    product = db.session.get(Product, product_id)
    if product is None:
        return []
    return [[v.id, v.size, v.description] for v in product_variants(product)]


def get_cart(create=False):
    """The current customer's PENDING cart (created on demand when ``create``)."""
    customer = get_or_create_current_customer() if create else get_current_customer()
    if customer is None:
        return None
    carts = (
        db.session.query(Cart).filter_by(customer_id=customer.id, status="PENDING").order_by(Cart.id).all()
    )
    if len(carts) > 1:
        # Shouldn't happen; keep the newest and retire the rest rather than lose items silently.
        log.warning(
            "Customer %s had %s pending carts; keeping cart %s", customer.id, len(carts), carts[-1].id
        )
        for extra in carts[:-1]:
            extra.status = "CANCELLED"
    if carts:
        return carts[-1]
    if not create:
        return None
    cart = Cart(customer_id=customer.id, status="PENDING")
    db.session.add(cart)
    db.session.flush()
    return cart


def item_count():
    cart = get_cart()
    return len(cart.pending_items) if cart else 0


def recalculate(cart):
    """Recompute every pending item's totals and the cart totals (no commit)."""
    merchandise = shipping = taxes = discount = ZERO
    for item in cart.pending_items:
        item.total_shipping = _money(item.shipping_base_charge) + _money(item.shipping_up_charge)
        item.total_tax = _money(item.merchandise_tax) + _money(item.shipping_tax)
        item.total_discount = _money(item.merchandise_discount) + _money(item.shipping_discount)
        item.total_item = (
            _money(item.product_price) + item.total_shipping + item.total_tax - item.total_discount
        )
        merchandise += _money(item.product_price)
        shipping += item.total_shipping
        taxes += item.total_tax
        discount += item.total_discount
    # Shipping is charged per order, by the chosen method (free over its threshold).
    if cart.pending_items:
        shipping += method_for(cart.shipping_method).charge(merchandise)
    cart.total_merchandise = merchandise
    cart.total_shipping = shipping
    cart.total_taxes = taxes
    cart.total_discount = discount
    # Discounts are stored as positive amounts, so they reduce the total.
    cart.total_cart = merchandise + shipping + taxes - discount


def add_item(product_id, variant_id=None):
    """Add one of a product (in the chosen size, else its default) to the cart."""
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        raise CartError("This product is not available.")
    variants = product_variants(product)
    if not variants:
        raise CartError("Product is currently out of stock")
    variant = next((v for v in variants if v.id == variant_id), None) or default_variant(variants)
    cart = get_cart(create=True)
    item = Item(
        product=product,
        variant=variant,
        product_sku=product.sku,
        product_name=product.name,
        product_price=line_price(product, variant),
        status="PENDING",
    )
    cart.items.append(item)
    recalculate(cart)
    db.session.commit()
    return item


def _own_pending_item(item_id):
    cart = get_cart()
    if cart is None or not item_id:
        return None
    return next((item for item in cart.pending_items if item.id == item_id), None)


def remove_item(item_id):
    """Remove an item from the current customer's cart. Returns False if it isn't theirs."""
    item = _own_pending_item(item_id)
    if item is None:
        return False
    cart = item.cart
    cart.items.remove(item)  # delete-orphan deletes the row
    recalculate(cart)
    db.session.commit()
    return True


def change_variant(item_id, variant_id):
    """Switch a cart item to another size of the same product and reprice it."""
    item = _own_pending_item(item_id)
    if item is None or item.product is None:
        return False
    variant = next((v for v in product_variants(item.product) if v.id == variant_id), None)
    if variant is None:
        return False
    item.variant = variant
    item.product_price = line_price(item.product, variant)
    recalculate(item.cart)
    db.session.commit()
    return True


def adopt_guest_cart(guest_customer_id, customer):
    """On login, move a guest's pending cart items into the user's cart so nothing is lost."""
    if not guest_customer_id or guest_customer_id == customer.id:
        return
    guest_cart = (
        db.session.query(Cart)
        .filter_by(customer_id=guest_customer_id, status="PENDING")
        .order_by(Cart.id.desc())
        .first()
    )
    if guest_cart is None or not guest_cart.pending_items:
        return
    user_cart = (
        db.session.query(Cart)
        .filter_by(customer_id=customer.id, status="PENDING")
        .order_by(Cart.id.desc())
        .first()
    )
    if user_cart is None:
        guest_cart.customer_id = customer.id
        db.session.commit()
        return
    for item in list(guest_cart.pending_items):
        item.cart = user_cart  # moves it between the two carts' item lists
    guest_cart.status = "CANCELLED"
    recalculate(user_cart)
    db.session.commit()
