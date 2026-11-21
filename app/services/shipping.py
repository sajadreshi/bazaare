"""Shipping methods, their prices and delivery estimates, and carrier tracking links (US only for now)."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from app.extension import db
from app.models import Holiday


@dataclass(frozen=True)
class ShippingMethod:
    code: str
    name: str
    price: Decimal
    min_days: int  # business days after the order is placed
    max_days: int
    free_over: Decimal | None = None  # merchandise subtotal at or above which shipping is free

    def charge(self, merchandise):
        if self.free_over is not None and merchandise >= self.free_over:
            return Decimal("0.00")
        return self.price

    @property
    def days_label(self):
        return (
            f"{self.min_days}–{self.max_days} business days"
            if self.min_days != self.max_days
            else f"{self.min_days} business day{'s' if self.min_days != 1 else ''}"
        )


# Placeholder prices: confirm with the client.
METHODS = {
    "STANDARD": ShippingMethod("STANDARD", "Standard", Decimal("5.99"), 3, 5, free_over=Decimal("50.00")),
    "EXPRESS": ShippingMethod("EXPRESS", "Express", Decimal("14.99"), 1, 2),
}
DEFAULT_METHOD = "STANDARD"

# Tracking page per carrier; {number} is replaced with the tracking number.
CARRIERS = {
    "USPS": "https://tools.usps.com/go/TrackConfirmAction?tLabels={number}",
    "UPS": "https://www.ups.com/track?tracknum={number}",
    "FedEx": "https://www.fedex.com/fedextrack/?trknbr={number}",
    "DHL": "https://www.dhl.com/us-en/home/tracking.html?tracking-id={number}",
    "Other": None,
}


def method_for(code):
    return METHODS.get(code or DEFAULT_METHOD, METHODS[DEFAULT_METHOD])


def _days_off(start, end):
    holidays = db.session.query(Holiday).filter(Holiday.holiday_date >= start, Holiday.holiday_date <= end)
    return {h.holiday_date.date() for h in holidays if h.holiday_date}


def add_business_days(start, days):
    """The date `days` business days after `start` (skipping weekends and admin Holidays)."""
    off = _days_off(
        datetime.datetime.combine(start, datetime.time()),
        datetime.datetime.combine(start + datetime.timedelta(days=days * 3 + 14), datetime.time()),
    )
    current, added = start, 0
    while added < days:
        current += datetime.timedelta(days=1)
        if current.weekday() < 5 and current not in off:
            added += 1
    return current


def estimated_delivery(code, placed=None):
    """(earliest, latest) delivery dates for an order placed on `placed` (default today)."""
    method = method_for(code)
    placed = placed or datetime.date.today()
    return add_business_days(placed, method.min_days), add_business_days(placed, method.max_days)


def tracking_url(carrier, number):
    template = CARRIERS.get(carrier)
    return template.format(number=number) if template and number else None
