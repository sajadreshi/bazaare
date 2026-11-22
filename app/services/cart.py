"""The shopping cart: adding, removing and re-sizing items, and keeping totals right.

A customer has at most one PENDING cart. Prices are computed here, from the
database, never taken from the browser.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.extension import db
from app.models import Cart, Item, Product
from app.services import promotions, tax
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
    """Price of one item: the option's own price, else the product's."""
    if variant is not None and variant.price is not None:
        return _money(variant.price)
    return _money(product.price)


def product_variants(product):
    return list(product.options)


def default_variant(variants):
    """The option selected at first: the default if it's in stock, else the first one in stock."""
    available = [v for v in variants if v.in_stock]
    return next((v for v in available if v.is_default), available[0] if available else None)


def variant_choices(product_id):
    """[[id, name, note], ...] for the cart's "change size" dropdown (sold-out options left out)."""
    product = db.session.get(Product, product_id)
    if product is None:
        return []
    return [[v.id, v.name, ""] for v in product_variants(product) if v.in_stock]


def _in_cart(cart, variant):
    return sum(1 for item in cart.pending_items if item.size_id == variant.id) if cart else 0


def check_stock(cart, variant, adding=1):
    """Raise CartError if the bag can't hold ``adding`` more of this option."""
    available = variant.available
    name = f"{variant.product.name} ({variant.name})"
    if available <= 0:
        raise CartError(f"Sorry, {name} is sold out.")
    if _in_cart(cart, variant) + adding > available:
        raise CartError(f"Sorry, only {available} of {name} left.")


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
    customer = cart.customer
    items = cart.pending_items
    # Coupon first: it lowers each line's price, so tax and free shipping see the discounted bag.
    subtotal = sum((_money(i.product_price) for i in items), ZERO)
    coupon = cart.coupon
    if coupon is not None and promotions.problem(coupon, subtotal) is None:
        off = promotions.discount(coupon, subtotal)
    else:
        off = ZERO
    for item, share in zip(items, _split(off, [_money(i.product_price) for i in items]), strict=True):
        item.merchandise_discount = share
    sales_tax = tax.quote(customer.shipping_address if customer else None)
    _allocate_tax(items, sales_tax)
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
        shipping += method_for(cart.shipping_method).charge(merchandise - discount)
    if sales_tax.tax_shipping:
        taxes += sales_tax.on(shipping)
    cart.tax_rate = sales_tax.rate if sales_tax.applies else None
    cart.tax_region = sales_tax.region if sales_tax.applies else None
    cart.total_merchandise = merchandise
    cart.total_shipping = shipping
    cart.total_taxes = taxes
    cart.total_discount = discount
    # Discounts are stored as positive amounts, so they reduce the total.
    cart.total_cart = merchandise + shipping + taxes - discount


def _split(total, weights):
    """Split ``total`` across lines in proportion to ``weights``; rounding cents go to the last line."""
    base = sum(weights, ZERO)
    shares, left = [], total
    for index, weight in enumerate(weights):
        share = left if index == len(weights) - 1 or not base else _money(total * weight / base)
        shares.append(share)
        left -= share
    return shares


def _allocate_tax(items, sales_tax):
    """Tax the bag's (discounted) merchandise once, so it matches rate x subtotal, then split it
    across the lines in proportion to their price."""
    taxable = [_money(i.product_price) - _money(i.merchandise_discount) for i in items]
    total = sales_tax.on(sum(taxable, ZERO))
    for item, share in zip(items, _split(total, taxable), strict=True):
        item.merchandise_tax = share
        item.shipping_tax = ZERO  # shipping tax is added once for the whole order


def add_item(product_id, variant_id=None):
    """Add one of a product (in the chosen size, else its default) to the cart."""
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        raise CartError("This product is not available.")
    variants = product_variants(product)
    variant = next((v for v in variants if v.id == variant_id), None) or default_variant(variants)
    if variant is None:
        raise CartError("Sorry, this product is sold out.")
    check_stock(get_cart(), variant)
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
    if variant.id != item.size_id:
        try:
            check_stock(item.cart, variant)
        except CartError:
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
