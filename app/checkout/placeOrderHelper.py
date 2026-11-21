import logging

from app.checkout.commonutil import getCartObj
from app.checkout.getcarthelper import get_current_cart
from app.checkout.orders import create_order_from_cart
from app.checkout.PaymentHelper import doPayment
from app.checkout.placeOrderStatus import PlaceOrderStatus
from app.extension import db
from app.models import Cart, Item, Payment, utcnow

log = logging.getLogger(__name__)


def placeOrder(place_order_frm):
    status = PlaceOrderStatus()
    current_cart = get_current_cart()
    if not getCartObj(current_cart):
        status.error = "Your cart is empty"
    elif not current_cart.get("is_shipping_complete"):
        status.error = "Please complete your shipping address"
    elif not current_cart.get("is_billing_complete"):
        status.error = "Please complete your billing address"
    elif not current_cart.get("is_delivery_complete"):
        status.error = "Please choose your delivery date"
    else:
        status = processCart(place_order_frm, current_cart, status)
    return status


def processCart(place_order_frm, current_cart, status):
    """Charge the cart and turn it into an Order in a single transaction.

    Either everything is saved (order + items, payment, cart COMPLETED) or
    nothing is: any failure rolls back and the cart stays PENDING.
    """
    cart_id = getCartObj(current_cart).get("cart_id")
    try:
        # Lock the cart row so a double-submitted order can't be charged twice.
        cart = db.session.query(Cart).filter(Cart.id == cart_id).with_for_update().one()
        if cart.status != "PENDING":
            status.error = "This order has already been placed."
            db.session.rollback()
            return status

        payment_status = doPayment(place_order_frm, current_cart)
        if not payment_status.isSuccess:
            db.session.rollback()
            status.error = payment_status.error or "Payment was not approved."
            return status

        order = create_order_from_cart(cart)
        now = utcnow()
        db.session.add(
            Payment(
                payment_method=payment_status.paymentMethod,
                cart_id=cart_id,
                order_id=order.id,
                transaction_id=payment_status.transactionId,
                transaction_status=payment_status.transactionStatus,
                auth_code=payment_status.authCode,
                requested_amount=payment_status.requestedAmount,
                approved_amount=payment_status.approvedAmount,
            )
        )
        for item in db.session.query(Item).filter(Item.cart_id == cart_id):
            item.status = "COMPLETED"
            item.updated_at = now
        cart.status = "COMPLETED"
        cart.updated_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("Placing order for cart %s failed", cart_id)
        status.error = "Error occurred while processing your cart. Please try again"
        return status

    status.isSuccess = True
    status.cartId = cart_id
    status.orderId = order.id
    return status
