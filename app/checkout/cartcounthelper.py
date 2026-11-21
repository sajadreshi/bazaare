from flask import session
from sqlalchemy import text

from app.extension import db

count_query = """
    select c.id as cart_id, count(ci.id) as item_count
    from cart c
    inner join item ci on ci.cart_id = c.id
    where c.customer_id = :customerId and c.status = 'PENDING'
    group by c.id
"""


def get_cart_count():
    """Cart id and item count for the header badge (``item_count`` is 0 when empty)."""
    cart_count = {"cart_id": None, "item_count": 0}
    customer_id = session.get("customer_id")
    if not customer_id:
        return cart_count
    row = db.session.execute(text(count_query), {"customerId": customer_id}).first()
    if row:
        cart_count["cart_id"] = row.cart_id
        cart_count["item_count"] = row.item_count
    return cart_count
