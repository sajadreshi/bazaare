"""Taking payment for an order.

Card details are never stored by the shop: a real gateway integration should
keep them on the provider's side and return only a transaction id / auth code.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

log = logging.getLogger(__name__)

PAYMENT_METHODS = [("COD", "Cash On Delivery")]


@dataclass
class PaymentResult:
    method: str
    requested_amount: Decimal
    approved: bool = False
    error: str = ""
    transaction_id: str = ""
    transaction_status: str = "PENDING"
    auth_code: str = ""
    approved_amount: Decimal = Decimal("0.00")


def take_payment(method, amount):
    result = PaymentResult(method=method, requested_amount=Decimal(amount or 0))
    match method:
        case "COD":
            # Cash on delivery: approved now, collected by the courier.
            result.approved = True
            result.transaction_status = "APPROVED"
            result.approved_amount = result.requested_amount
        case "creditCard" | "payPal":
            # Gateway integrations (e.g. Stripe, PayPal) go here.
            result.error = "This payment method is not available yet."
        case _:
            log.warning("Unknown payment method %r", method)
            result.error = "Please choose a payment method."
    return result
