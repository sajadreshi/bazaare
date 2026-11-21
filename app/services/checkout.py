"""Checkout: addresses, delivery date and placing the order."""

import logging
from dataclasses import dataclass

from app.extension import db
from app.models import Address, Cart, Payment, utcnow
from app.services.cart import get_cart, recalculate
from app.services.customers import get_or_create_current_customer
from app.services.orders import create_order_from_cart
from app.services.payments import take_payment
from app.services.shipping import METHODS
from app.services.stock import OutOfStock, take_for_cart

log = logging.getLogger(__name__)

ADDRESS_FIELDS = ("first_name", "last_name", "address1", "address2", "city", "state", "zip", "email", "phone")
REQUIRED_ADDRESS_FIELDS = (
    "first_name",
    "last_name",
    "address1",
    "city",
    "state",
    "zip",
    "country",
    "email",
    "phone",
)


def address_complete(address):
    return address is not None and all((getattr(address, f) or "").strip() for f in REQUIRED_ADDRESS_FIELDS)


@dataclass
class CheckoutStatus:
    shipping: bool
    billing: bool
    delivery: bool

    @property
    def ready(self):
        return self.shipping and self.billing and self.delivery


def checkout_status(cart):
    customer = cart.customer if cart else None
    return CheckoutStatus(
        shipping=address_complete(customer.shipping_address if customer else None),
        billing=address_complete(customer.billing_address if customer else None),
        delivery=True,  # a shipping method is always set (Standard unless the shopper picks another)
    )


def save_address(form, kind):
    """Save a shipping or billing address for the current customer.

    Addresses are never edited in place (orders point at them), so each save
    is a new row. A first shipping address also becomes the billing address.
    """
    address = Address(**{field: getattr(form, field).data for field in ADDRESS_FIELDS})
    db.session.add(address)
    customer = get_or_create_current_customer()
    if kind == "shipping":
        customer.shipping_address = address
        if customer.billing_address is None:
            customer.billing_address = address
    else:
        customer.billing_address = address
    db.session.commit()
    return address


def save_shipping_method(code):
    """Choose Standard/Express for the current cart. Returns False for an unknown method."""
    cart = get_cart()
    if cart is None or code not in METHODS:
        return False
    cart.shipping_method = code
    recalculate(cart)
    db.session.commit()
    return True


@dataclass
class PlaceOrderResult:
    order: object = None
    error: str = ""

    @property
    def ok(self):
        return self.order is not None


def place_order(payment_method):
    """Charge the cart and turn it into an Order in a single transaction.

    Either everything is saved (order + items, payment, cart COMPLETED) or
    nothing is: any failure rolls back and the cart stays PENDING.
    """
    cart = get_cart()
    if cart is None or not cart.pending_items:
        return PlaceOrderResult(error="Your cart is empty")
    status = checkout_status(cart)
    if not status.shipping:
        return PlaceOrderResult(error="Please complete your shipping address")
    if not status.billing:
        return PlaceOrderResult(error="Please complete your billing address")

    cart_id = cart.id
    try:
        # Lock the cart row so a double-submitted order can't be charged twice.
        cart = db.session.query(Cart).filter(Cart.id == cart_id).with_for_update().populate_existing().one()
        if cart.status != "PENDING":
            db.session.rollback()
            return PlaceOrderResult(error="This order has already been placed.")
        recalculate(cart)
        take_for_cart(cart)
        payment = take_payment(payment_method, cart.total_cart)
        if not payment.approved:
            db.session.rollback()
            return PlaceOrderResult(error=payment.error or "Payment was not approved.")

        order = create_order_from_cart(cart)
        db.session.add(
            Payment(
                payment_method=payment.method,
                cart_id=cart.id,
                order_id=order.id,
                transaction_id=payment.transaction_id,
                transaction_status=payment.transaction_status,
                auth_code=payment.auth_code,
                requested_amount=payment.requested_amount,
                approved_amount=payment.approved_amount,
            )
        )
        now = utcnow()
        for item in cart.pending_items:
            item.status = "COMPLETED"
            item.updated_at = now
        cart.status = "COMPLETED"
        cart.updated_at = now
        db.session.commit()
    except OutOfStock as error:
        db.session.rollback()
        return PlaceOrderResult(error=str(error))
    except Exception:
        db.session.rollback()
        log.exception("Placing order for cart %s failed", cart_id)
        return PlaceOrderResult(error="Error occurred while processing your cart. Please try again")
    return PlaceOrderResult(order=order)
