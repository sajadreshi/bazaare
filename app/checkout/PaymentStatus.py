from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentStatus:
    """Result of a payment attempt.

    Card details are never stored here or in the database: a real gateway
    integration should keep them on the provider's side and return a
    transaction id / auth code only.
    """

    paymentMethod: str
    requestedAmount: Decimal
    isSuccess: bool = False
    error: str = ""
    transactionId: str = ""
    transactionStatus: str = "PENDING"
    authCode: str = ""
    approvedAmount: Decimal = Decimal("0.00")
