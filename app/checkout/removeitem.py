from sqlalchemy import delete

from app.checkout.calculatecart import calculate_cart
from app.checkout.commonutil import get_current_pending_cart
from app.extension import db
from app.models import Item


def delete_item(itemId):
    cart = get_current_pending_cart()
    if cart and item_in_cart(cart.first(), itemId):
        statement = delete(Item).where(Item.id == itemId)
        db.session.execute(statement)
        db.session.commit()
        calculate_cart()


def item_in_cart(cart, itemId):
    is_item_present = False
    items = db.session.query(Item).filter(Item.id == itemId)
    if items and items.count() > 0:
        for item in items.all():
            if item.cart_id == cart.id:
                is_item_present = True
                break
    return is_item_present
