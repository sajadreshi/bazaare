"""Order emails: confirmed, shipped (with tracking), delivered, and a new-order alert for the shop.

Each email is built by ``build(kind, order)`` (also used for the admin previews) and sent
with ``send(kind, order)``. Sending never raises: a mail problem is logged, the order goes on.
"""

import logging
from dataclasses import dataclass

from flask import current_app, render_template, request, url_for

from app import mailer
from app.services import inventory

log = logging.getLogger(__name__)

KINDS = {
    "confirmed": "Order confirmed (to the shopper)",
    "shipped": "Order shipped (to the shopper)",
    "delivered": "Order delivered (to the shopper)",
    "admin_new_order": "New order alert (to you)",
}


@dataclass
class Email:
    subject: str
    recipients: list
    html: str
    text: str


def _absolute(url):
    if not url or url.startswith(("http://", "https://")):
        return url
    return request.url_root.rstrip("/") + url


def _url(endpoint, **values):
    return url_for(endpoint, _external=True, **values)


def customer_contact(order):
    """(first name, email, registered?) for the person who placed the order."""
    customer = order.customer
    user = customer.user if customer else None
    address = order.shipping_address or order.billing_address
    if user is not None:
        return user.first_name, user.email, True
    if address is not None:
        return address.first_name, address.email, False
    return None, None, False


def _payment_label(order):
    methods = [p.payment_method for p in order.payments]
    if not methods or methods == ["COD"]:
        return "Cash on delivery"
    return ", ".join(methods)


def wants_updates(order):
    """Shipping/delivery emails respect a registered shopper's 'Order updates by email' choice."""
    user = order.customer.user if order.customer else None
    return user is None or user.transactional_email is not False


def alert_address():
    return inventory.settings().order_alert_email or current_app.config.get("ADMIN_EMAIL")


def build(kind, order):
    name, email, registered = customer_contact(order)
    support = inventory.settings().support_email or "support@bazaare.com"
    common = {
        "order": order,
        "name": name,
        "support_email": support,
        "shop_url": _url("main.home"),
        "url": _url,
        "absolute": _absolute,
        "payment_label": _payment_label(order),
        "cash": _payment_label(order) == "Cash on delivery",
        "order_url": _url("customer.orderDetails", orderId=order.id) if registered else None,
        "hand": order.carrier == "Hand delivery",
    }
    if kind == "confirmed":
        subject = f"Your BazaarE' order {order.number} is confirmed"
        intro = "Thank you! Your order is confirmed and we're getting it ready."
        recipients = [email]
        template = "email/order_confirmed.html"
        link, link_label = common["order_url"], "View your order"
    elif kind == "shipped":
        subject = f"Your BazaarE' order {order.number} is on its way"
        if common["hand"]:
            intro = "We're delivering your order to you by hand."
        else:
            intro = f"Your order has shipped with {order.carrier}." + (
                f" Tracking number: {order.tracking_number}." if order.tracking_number else ""
            )
        recipients = [email]
        template = "email/order_shipped.html"
        link, link_label = order.tracking_url, "Track your parcel"
    elif kind == "delivered":
        subject = f"Your BazaarE' order {order.number} was delivered"
        intro = "Your order was delivered. We hope you love it!"
        recipients = [email]
        template = "email/order_delivered.html"
        link, link_label = common["order_url"], "View your order"
    elif kind == "admin_new_order":
        from app.adminapp.views import order_customer  # admin helper; imported late

        person, person_email, person_kind = order_customer(order)
        subject = f"New order {order.number}: ${order.total:.2f} from {person}"
        intro = f"{person} ({person_kind}, {person_email or 'no email'}) placed an order."
        recipients = [alert_address()]
        template = "email/admin_new_order.html"
        admin_url = _url("order.details_view", id=order.id)
        common.update(
            customer_name=person,
            customer_email=person_email,
            customer_kind=person_kind,
            admin_url=admin_url,
            alert_email=recipients[0],
        )
        link, link_label = admin_url, "Open in admin"
    else:
        raise ValueError(f"Unknown email kind {kind!r}")
    html = render_template(template, **common)
    text = render_template(
        "email/order.txt",
        heading=subject,
        intro=intro,
        link=link,
        link_label=link_label,
        **common,
    )
    return Email(subject, [r for r in recipients if r], html, text)


def send(kind, order):
    """Build and send one email. Returns the Email, or None if there was no one to send it to."""
    try:
        email = build(kind, order)
        if not email.recipients:
            log.info("No address for %s email about %s", kind, order.number)
            return None
        reply_to = inventory.settings().support_email
        mailer.send(email.subject, email.recipients, email.html, email.text, reply_to=reply_to)
        return email
    except Exception:
        log.exception("Couldn't send the %s email for order %s", kind, order.number)
        return None


def order_placed(order):
    send("confirmed", order)
    send("admin_new_order", order)


def status_changed(order, previous):
    if not wants_updates(order):
        return
    if order.status == "SHIPPED" and previous == "PLACED":
        send("shipped", order)
    elif order.status == "DELIVERED" and previous in ("PLACED", "SHIPPED"):
        send("delivered", order)
