from app.checkout.commonutil import getCartObj
from app.checkout.PaymentStatus import PaymentStatus


def doPayment(payment_form, current_cart):
    payment_method = payment_form.payment_method.data
    cart_obj = getCartObj(current_cart)
    match payment_method:
        case "COD":
            return doPaymentWithCOD(payment_form, cart_obj)

        case "creditCard":
            return doPaymentWithCreditCard(payment_form, cart_obj)

        case "payPal":
            return doPaymentWithPayPal(payment_form, cart_obj)


def doPaymentWithCOD(payment_form, cart_obj):
    pStatus = initializePayment(payment_form, cart_obj)
    pStatus.isSuccess = True
    pStatus.transactionStatus = "APPROVED"
    pStatus.approvedAmount = cart_obj.get("total_cart")
    return pStatus


def doPaymentWithCreditCard(payment_form, cart_obj):
    # payment integration with payment gateway goes here
    return initializePayment(payment_form, cart_obj)


def doPaymentWithPayPal(payment_form, cart_obj):
    # payment integration with paypal gateway goes here
    return initializePayment(payment_form, cart_obj)


def initializePayment(payment_form, cart_obj):
    paymentStatus = PaymentStatus(
        False,
        "",
        payment_form.payment_method.data,
        "",
        "",
        0,
        0,
        "",
        "PENDING",
        "",
        cart_obj.get("total_cart"),
        0.00,
    )
    return paymentStatus


def getValueFromCart(current_cart, field):
    try:
        return getCartObj(current_cart).get(field)
    except:
        return None
