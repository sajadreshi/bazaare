"""Orders: created from a paid cart, then read back by their owner."""

from app.extension import db
from app.models import Order, OrderItem
from app.services.shipping import method_for


def create_order_from_cart(cart):
    """Copy a cart, its items and the customer's current addresses into a new Order.

    Runs inside the caller's transaction (no commit here).
    """
    customer = cart.customer
    order = Order(
        customer_id=cart.customer_id,
        cart_id=cart.id,
        status="PLACED",
        total_merchandise=cart.total_merchandise or 0,
        total_shipping=cart.total_shipping or 0,
        total_taxes=cart.total_taxes or 0,
        total_discount=cart.total_discount or 0,
        total=cart.total_cart or 0,
        shipping_method=method_for(cart.shipping_method).code,
        shipping_address_id=customer.shipping_address_id if customer else None,
        billing_address_id=customer.billing_address_id if customer else None,
    )
    for item in cart.pending_items:
        product, variant = item.product, item.variant
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                variant_id=item.size_id,
                sku=item.product_sku,
                name=item.product_name or (product.name if product else item.product_sku),
                variant_name=variant.name if variant else None,
                image=product.main_image if product else None,
                price=item.product_price or 0,
                shipping=item.total_shipping or 0,
                tax=item.total_tax or 0,
                discount=item.total_discount or 0,
            )
        )
    db.session.add(order)
    db.session.flush()  # assigns order.id
    return order


def get_customer_order(order_id, customer_id):
    """The order if it belongs to this customer, else None."""
    if not customer_id:
        return None
    return db.session.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()


def list_customer_orders(customer_id):
    query = db.session.query(Order).filter(Order.customer_id == customer_id)
    return query.order_by(Order.placed_at.desc(), Order.id.desc()).all()
