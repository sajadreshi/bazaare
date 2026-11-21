from decimal import Decimal

from app.checkout.commonutil import get_current_pending_cart
from app.extension import db
from app.models import Item


def calculate_cart():
    cart = get_current_pending_cart()
    if cart:
        perform_calculation(cart)


def perform_calculation(cart):
    cart_total = 0.00
    total_merchandise = 0.00
    total_shipping = 0.00
    total_taxes = 0.00
    total_discount = 0.00
    cur_cart = cart.first()
    items = db.session.query(Item).filter(Item.cart_id == cur_cart.id, Item.status == "PENDING")
    if items and items.count() > 0:
        for item in items.all():
            item_total_shipping = Decimal(item.shipping_base_charge) + Decimal(item.shipping_up_charge)
            item_total_taxes = Decimal(item.merchandise_tax) + Decimal(item.shipping_tax)
            item_total_discount = Decimal(item.merchandise_discount) + Decimal(item.shipping_discount)
            total_merchandise = Decimal(total_merchandise) + Decimal(item.product_price)
            total_shipping = Decimal(total_shipping) + Decimal(item_total_shipping)
            total_taxes = Decimal(total_taxes) + Decimal(item_total_taxes)
            total_discount = Decimal(total_discount) + Decimal(item_total_discount)
            item.total_shipping = item_total_shipping
            item.total_tax = item_total_taxes
            item.total_discount = item_total_discount
        # Discounts are stored as positive amounts, so they reduce the total.
        cart_total = (
            Decimal(total_merchandise)
            + Decimal(total_shipping)
            + Decimal(total_taxes)
            - Decimal(total_discount)
        )
        cart.update(
            {
                "total_merchandise": total_merchandise,
                "total_shipping": total_shipping,
                "total_taxes": total_taxes,
                "total_discount": total_discount,
                "total_cart": cart_total,
            }
        )
        db.session.commit()
