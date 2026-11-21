from dataclasses import dataclass


@dataclass
class PlaceOrderStatus:
    isSuccess: bool = False
    error: str = ""
    cartId: int | None = None
