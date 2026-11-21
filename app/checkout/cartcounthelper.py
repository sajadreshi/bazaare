from flask import session
from sqlalchemy import text

from app.extension import db

count_query = "select c.id as cart_id, count(ci.id) as item_count\
      from cart c \
      inner join item ci on ci.cart_id = c.id \
      inner join customer cu on cu.id = c.customer_id \
      where c.customer_id=:customerId and c.status='PENDING';"


def get_cart_count():
    cart_count = {}
    try:
        cart_count["cart_id"] = None
        cart_count["item_count"] = None
        curr_customer_id = session.get("customer_id")
        value = {"customerId": curr_customer_id}
        sql = text(count_query)
        result = db.session.execute(sql, value)
        for row in result:
            cart_count["cart_id"] = row.cart_id
            cart_count["item_count"] = row.item_count
    except:
        return cart_count
    return cart_count
