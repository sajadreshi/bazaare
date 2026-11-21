import logging
from decimal import Decimal

from app.checkout.commonutil import getCartObj
from app.checkout.PaymentStatus import PaymentStatus

log = logging.getLogger(__name__)


def doPayment(payment_form, current_cart):
    payment_method = payment_form.payment_method.data
    cart_obj = getCartObj(current_cart) or {}
    status = PaymentStatus(
        paymentMethod=payment_method,
        requestedAmount=Decimal(cart_obj.get("total_cart") or 0),
    )
    match payment_method:
        case "COD":
            return doPaymentWithCOD(status)
        case "creditCard" | "payPal":
            # Gateway integrations (e.g. Stripe, PayPal) go here. They must tokenize
            # card data on the provider's side; never pass raw card numbers through.
            status.error = "This payment method is not available yet."
            return status
        case _:
            log.warning("Unknown payment method %r", payment_method)
            status.error = "Please choose a payment method."
            return status


def doPaymentWithCOD(status):
    status.isSuccess = True
    status.transactionStatus = "APPROVED"
    status.approvedAmount = status.requestedAmount
    return status
