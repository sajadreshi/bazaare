"""Shippo: shipping rates, labels and tracking updates (https://docs.goshippo.com).

Plain HTTPS to https://api.goshippo.com with `Authorization: ShippoToken <key>`.
Test keys start with shippo_test_ and produce sample labels that can't be mailed.
"""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from flask import current_app

from app.extension import db
from app.models import Order, utcnow

log = logging.getLogger(__name__)

API = "https://api.goshippo.com"
REQUIRED_FROM = ("name", "street1", "city", "state", "zip", "phone", "email")
# Shippo provider names -> the carrier keys used on orders (services.shipping.CARRIERS).
PROVIDERS = {"USPS": "USPS", "UPS": "UPS", "FEDEX": "FedEx", "DHL EXPRESS": "DHL", "DHL": "DHL"}


class ShippoError(Exception):
    """Something the admin should see (bad address, no rates, label refused...)."""


@dataclass
class Rate:
    object_id: str
    provider: str
    service: str
    amount: Decimal
    currency: str
    days: int | None
    terms: str


def is_configured():
    config = current_app.config
    return bool(config.get("SHIPPO_API_KEY")) and all(config["SHIP_FROM"].get(f) for f in REQUIRED_FROM)


def missing_settings():
    config = current_app.config
    missing = [] if config.get("SHIPPO_API_KEY") else ["SHIPPO_API_KEY"]
    missing += [f"SHIP_FROM_{f.upper()}" for f in REQUIRED_FROM if not config["SHIP_FROM"].get(f)]
    return missing


def is_test_mode():
    return (current_app.config.get("SHIPPO_API_KEY") or "").startswith("shippo_test_")


def _request(method, path, payload=None):
    """Call the Shippo API and return the decoded JSON (raises ShippoError)."""
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"ShippoToken {current_app.config['SHIPPO_API_KEY']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:500]
        log.warning("Shippo %s %s failed: %s %s", method, path, error.code, detail)
        raise ShippoError(f"Shippo refused the request ({error.code}): {detail}") from error
    except urllib.error.URLError as error:
        raise ShippoError(f"Couldn't reach Shippo: {error.reason}") from error


def _address_to(order):
    address = order.shipping_address
    if address is None:
        raise ShippoError("This order has no shipping address.")
    return {
        "name": f"{address.first_name} {address.last_name}".strip(),
        "street1": address.address1,
        "street2": address.address2 or "",
        "city": address.city,
        "state": address.state,
        "zip": address.zip,
        "country": address.country or "US",
        "phone": address.phone or "",
        "email": address.email or "",
    }


def _parcel():
    length, width, height, weight = (part.strip() for part in current_app.config["SHIP_PARCEL"].split(","))
    return {
        "length": length,
        "width": width,
        "height": height,
        "distance_unit": "in",
        "weight": weight,
        "mass_unit": "oz",
    }


def _messages(obj):
    return "; ".join(m.get("text", "") for m in obj.get("messages") or [] if m.get("text"))


def get_rates(order):
    """Ask Shippo what it costs to send this order, cheapest first."""
    shipment = _request(
        "POST",
        "/shipments/",
        {
            "address_from": current_app.config["SHIP_FROM"],
            "address_to": _address_to(order),
            "parcels": [_parcel()],
            "metadata": order.number,
            "async": False,
        },
    )
    rates = []
    for raw in shipment.get("rates") or []:
        level = raw.get("servicelevel") or {}
        rates.append(
            Rate(
                object_id=raw["object_id"],
                provider=raw.get("provider", ""),
                service=level.get("name") or raw.get("servicelevel_name") or "",
                amount=Decimal(str(raw.get("amount", "0"))),
                currency=raw.get("currency", "USD"),
                days=raw.get("estimated_days"),
                terms=raw.get("duration_terms") or "",
            )
        )
    if not rates:
        raise ShippoError(_messages(shipment) or "Shippo returned no rates for this address.")
    return sorted(rates, key=lambda r: r.amount)


def buy_label(order, rate_id):
    """Buy the label for the chosen rate and mark the order shipped with its tracking number."""
    transaction = _request(
        "POST",
        "/transactions/",
        {"rate": rate_id, "label_file_type": "PDF", "metadata": order.number, "async": False},
    )
    if transaction.get("status") != "SUCCESS":
        raise ShippoError(_messages(transaction) or f"Label purchase failed ({transaction.get('status')}).")
    rate = transaction.get("rate")
    provider = (rate.get("provider") if isinstance(rate, dict) else None) or transaction.get("provider") or ""
    order.carrier = PROVIDERS.get(provider.upper(), "Other")
    order.tracking_number = (transaction.get("tracking_number") or "")[:64]
    order.label_url = transaction.get("label_url")
    order.shippo_transaction_id = transaction.get("object_id")
    if order.status == "PLACED":
        order.status = "SHIPPED"
        order.shipped_at = utcnow()
    db.session.commit()
    return order


def fresh_label_url(order):
    """Label links expire; fetch a current one from the transaction."""
    if not order.shippo_transaction_id:
        return order.label_url
    transaction = _request("GET", f"/transactions/{order.shippo_transaction_id}")
    order.label_url = transaction.get("label_url") or order.label_url
    db.session.commit()
    return order.label_url


def handle_tracking_update(payload):
    """Apply a `track_updated` webhook. Returns the order it changed, if any."""
    if payload.get("event") != "track_updated":
        return None
    data = payload.get("data") or {}
    number = data.get("tracking_number")
    status = ((data.get("tracking_status") or {}).get("status") or "").upper()
    order = Order.query.filter_by(tracking_number=number).first() if number else None
    if order is None:
        return None
    if status == "DELIVERED" and order.status in ("PLACED", "SHIPPED"):
        order.status = "DELIVERED"
        order.delivered_at = utcnow()
    elif status == "TRANSIT" and order.status == "PLACED":
        order.status = "SHIPPED"
        order.shipped_at = order.shipped_at or utcnow()
    elif status in ("RETURNED", "FAILURE"):
        log.warning("Shipment for %s reported %s", order.number, status)
        return order
    else:
        return order
    db.session.commit()
    log.info("%s is now %s (tracking update)", order.number, order.status)
    return order
