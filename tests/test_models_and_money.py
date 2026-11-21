from decimal import Decimal

from flask_login import AnonymousUserMixin

from app.checkout.calculatecart import perform_calculation
from app.extension import db
from app.models import Cart, Customer, Item, User


def test_user_flags_are_real(app):
    with app.app_context():
        admin = User.query.filter_by(email="user@admin.com").one()
        # is_admin is a stored column again, not a shadowing method.
        assert admin.is_admin is True
        assert "is_admin" in User.__table__.columns
        assert admin.is_authenticated is True
        assert admin.get_id() == str(admin.id)
        assert AnonymousUserMixin().is_authenticated is False


def test_cart_total_subtracts_discount_exactly(app):
    with app.app_context():
        customer = Customer(id=9000000001, customer_type="GUEST")
        db.session.add(customer)
        db.session.flush()
        cart = Cart(customer_id=customer.id, status="PENDING")
        db.session.add(cart)
        db.session.flush()
        # 0.1 + 0.2 style amounts that drift with floats.
        for price in ("10.10", "20.20", "0.30"):
            db.session.add(
                Item(
                    cart_id=cart.id,
                    product_sku="X",
                    product_price=Decimal(price),
                    shipping_base_charge=Decimal("1.10"),
                    merchandise_discount=Decimal("0.10"),
                    status="PENDING",
                )
            )
        db.session.commit()
        perform_calculation(db.session.query(Cart).filter(Cart.id == cart.id))
        cart = db.session.get(Cart, cart.id)
        assert cart.total_merchandise == Decimal("30.60")
        assert cart.total_shipping == Decimal("3.30")
        assert cart.total_discount == Decimal("0.30")
        assert cart.total_cart == Decimal("33.60")  # 30.60 + 3.30 - 0.30
