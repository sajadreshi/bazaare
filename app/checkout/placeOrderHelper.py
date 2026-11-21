from app import db
from app.checkout.getcarthelper import get_current_cart
from app.checkout.commonutil import get_current_pending_cart, getCartObj
from app.models import Cart, Item, Payment
from app.checkout.placeOrderStatus import PlaceOrderStatus
from app.checkout.PaymentHelper import doPayment
from datetime import datetime


def placeOrder(place_order_frm):
    status = PlaceOrderStatus(False, '', None)
    current_cart = get_current_cart()
    if current_cart:
        if not current_cart.get('is_shipping_complete'):
            status.isSuccess = False
            status.error = "Please complete your shipping address"
        elif not current_cart.get('is_billing_complete'):
            status.isSuccess = False
            status.error = "Please complete your billing address"
        elif not current_cart.get('is_delivery_complete'):
            status.isSuccess = False
            status.error = "Please choose your delivery date"
        else:
            status = processCart(place_order_frm, current_cart, status)

    return status


def processCart(place_order_frm, current_cart, status):

    cartId = getCartObj(current_cart).get('cart_id')
    try:
        setOrderState('LOCKED', cartId)
        paymentStatus = processPayment(place_order_frm, current_cart)

        if (paymentStatus.isSuccess):
            updateItem(cartId)
            setOrderState('COMPLETED', cartId)
            db.session.flush()
            db.session.commit()
            status.isSuccess = True
            status.cartId = cartId
        else:
            setOrderState('PENDING', cartId)
            status.isSuccess = False
            status.error = paymentStatus.error

    except:
        setOrderState('PENDING', cartId)
        status.isSuccess = False
        status.error = 'Error occured while processing your cart. Please try again'
    return status


def updateItem(cartId):
    items = db.session.query(Item).filter(Item.cart_id == cartId)
    if items and items.count() > 0:
        for item in items:
            item.status = 'COMPLETED'
            item.updated_at = datetime.now()


def setOrderState(state, cartId):
    cart = db.session.query(Cart).filter(Cart.id == cartId)
    if cart and cart.count() > 0:
        for c_cart in cart:
            c_cart.status = state
            c_cart.updated_at = datetime.now()
    db.session.commit()


def processPayment(place_order_frm, current_cart):
    cartId = getCartObj(current_cart).get('cart_id')
    paymentStatus = doPayment(place_order_frm, current_cart)
    if (paymentStatus.isSuccess):
        payment = Payment(payment_method=paymentStatus.paymentMethod,
                          cart_id=cartId,
                          account_number=paymentStatus.accountNumber,
                          account_name=paymentStatus.accountName,
                          expiry_month=paymentStatus.expiryMonth,
                          expiry_year=paymentStatus.expiryYear,
                          transaction_id=paymentStatus.transactionId,
                          transaction_status=paymentStatus.transactionStatus,
                          auth_code=paymentStatus.authCode,
                          requested_amount=paymentStatus.requestedAmount,
                          approved_amount=paymentStatus.approvedAmount
                          )
        db.session.add(payment)
        db.session.flush()
        db.session.commit()
    return paymentStatus
