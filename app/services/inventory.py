"""Inventory rules: the shop's stock threshold, and hiding/showing products as they sell out or are restocked.

Every option has a stock count. An option can be sold while its stock is above the
shop's threshold (Admin > Settings). When none of a product's options can be sold,
the product is hidden from the shop and marked ``sold_out_at``; when stock is added
again it comes back on its own. A product an admin hid by hand stays hidden.
"""

from flask import g, has_app_context

from app.extension import db
from app.models import Product, ShopSettings, utcnow


def settings():
    """The shop settings row (created with defaults the first time), cached for the request."""
    if has_app_context() and "shop_settings" in g:
        return g.shop_settings
    row = db.session.query(ShopSettings).order_by(ShopSettings.id).first()
    if row is None:
        row = ShopSettings(stock_threshold=0, low_stock_alert=3)
        db.session.add(row)
        db.session.flush()
    if has_app_context():
        g.shop_settings = row
    return row


def forget_settings():
    if has_app_context():
        g.pop("shop_settings", None)


def threshold():
    return settings().stock_threshold or 0


def low_stock_alert():
    return settings().low_stock_alert or 0


def is_sold_out(product):
    """True when the product has options and none of them can be sold."""
    return bool(product.options) and not any(option.in_stock for option in product.options)


def refresh(products):
    """Hide sold-out products and bring back restocked ones. Returns (hidden, restored) lists.

    Runs in the caller's transaction (no commit).
    """
    hidden, restored = [], []
    for product in products:
        if product is None:
            continue
        sold_out = is_sold_out(product)
        if sold_out and product.is_active:
            product.is_active = False
            product.sold_out_at = utcnow()
            hidden.append(product)
        elif not sold_out and product.sold_out_at is not None:
            product.is_active = True
            product.sold_out_at = None
            restored.append(product)
    return hidden, restored


def refresh_all():
    return refresh(db.session.query(Product).all())
