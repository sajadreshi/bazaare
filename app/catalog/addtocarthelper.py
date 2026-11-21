import uuid
from decimal import ROUND_HALF_UP, Decimal

from flask import session
from flask_login import current_user

from app.checkout.calculatecart import calculate_cart
from app.extension import db
from app.models import Cart, Customer, Item


def get_default_if_none(value):
    return value if value and value is not None else 0.00


def create_customer(customer_id):
    customer = db.session.query(Customer).filter(Customer.id == customer_id)
    if not customer or customer.count() == 0:
        customer_type = "REGISTERED" if current_user.is_authenticated else "GUEST"
        user_id = current_user.id if current_user.is_authenticated else None
        customer = Customer(id=customer_id, customer_type=customer_type, user_id=user_id)
        db.session.add(customer)
        db.session.commit()
    return customer_id


def fetch_current_user():
    curr_customer_id = session.get("customer_id")
    if not curr_customer_id:
        x = str(uuid.uuid4().int)
        curr_customer_id = int(x[:10])
        session["customer_id"] = curr_customer_id
    current_customer_id = create_customer(curr_customer_id)
    return current_customer_id


def create_new_cart(customer_id):
    cart = Cart(customer_id=customer_id, status="PENDING")
    db.session.add(cart)
    db.session.flush()
    return cart


def fetch_current_pending_cart():
    customer_id = fetch_current_user()
    cart = db.session.query(Cart).filter(Cart.customer_id == customer_id, Cart.status == "PENDING")
    if not cart or cart.count() == 0:
        return create_new_cart(customer_id)
    elif cart.count() > 1:
        cart.update({"status": "CANCELLED"})
        db.session.commit()
        return create_new_cart(customer_id)
    else:
        return cart.first()


def get_default_size(size_dic):
    # set first element by default
    default_size = next(iter(size_dic.values())) if size_dic else None
    for val in size_dic.values():
        if "default_size" in val and val.get("default_size") == 1:
            default_size = val
    return default_size


def get_size(product, size):
    if "sizes" in product:
        size_dic = product.get("sizes")
        s_size = size_dic.get(int(size) if size else "")
        if s_size:
            return s_size
        else:
            return get_default_size(size_dic)
    else:
        return None


def create_cart_item(product, selected_size, cur_cart):
    sale_price = get_default_if_none(product.get("product_sale_price"))
    quantity = get_default_if_none(selected_size.get("product_quantity"))
    item = Item(
        cart_id=cur_cart.id,
        product_id=product.get("product_id"),
        product_sku=product.get("product_sku"),
        product_name=product.get("product_name"),
        size_id=selected_size.get("size_id"),
        product_price=(Decimal(str(sale_price)) * Decimal(str(quantity))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
    )
    db.session.add(item)
    db.session.flush()
    db.session.commit()
    return item


def add_item_to_cart(product, size):
    cur_cart = fetch_current_pending_cart()
    create_cart_item(product, size, cur_cart)
    calculate_cart()
    return cur_cart
