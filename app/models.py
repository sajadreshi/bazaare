from datetime import UTC, datetime
from time import time

import jwt
from flask import current_app as app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extension import db


def utcnow():
    """Current UTC time as a naive datetime (the columns are timezone-naive)."""
    return datetime.now(UTC).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), index=True, nullable=False)
    email = db.Column(db.String(100), index=True, unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    marketing_email = db.Column(db.Boolean, nullable=True, default=False)
    transactional_email = db.Column(db.Boolean, nullable=True, default=True)
    marketing_sms = db.Column(db.Boolean, nullable=True, default=False)
    transactional_sms = db.Column(db.Boolean, nullable=True, default=True)
    cell_number = db.Column(db.String(20))
    roles = db.relationship("Role", secondary="user_roles")
    created_at = db.Column(db.DateTime, index=True, default=utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])["reset_password"]
        except (jwt.PyJWTError, KeyError):
            return None
        return db.session.get(User, id)

    def check_password(self, password):
        h = check_password_hash(self.password, password)
        return h

    # is_active / is_authenticated / is_anonymous / get_id come from UserMixin.
    # (Overriding them here used to shadow the is_admin column and made
    # is_authenticated always truthy.)

    def __repr__(self):
        return f"<User {self.email}>"


class Role(db.Model):
    __tablename__ = "role"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return self.name


class UserRoles(db.Model):
    __tablename__ = "user_roles"
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id", ondelete="CASCADE"))
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id", ondelete="CASCADE"))


class Product(db.Model):
    __tablename__ = "product"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), index=True, unique=True, nullable=False)
    name = db.Column(db.String(64), index=True, nullable=False)
    description = db.Column(db.String(300))
    retail_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_price = db.Column(db.Numeric(10, 2), nullable=False)
    main_image = db.Column(db.Unicode(128))
    alt1_image = db.Column(db.Unicode(128))
    alt2_image = db.Column(db.Unicode(128))
    alt3_image = db.Column(db.Unicode(128))
    is_handmade = db.Column(db.Boolean, default=False)
    is_sustainable = db.Column(db.Boolean, default=False)
    material = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=False)
    display = db.Column(db.Boolean, default=False)
    unit_quantity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    categories = db.relationship(
        "Category", secondary="category_product_rel", backref=db.backref("product", lazy="dynamic")
    )
    associations = db.relationship(
        "ProductAssociation",
        foreign_keys="ProductAssociation.source_product_id",
        back_populates="source_product",
        cascade="all, delete-orphan",
        order_by="(ProductAssociation.association_type, ProductAssociation.position, ProductAssociation.id)",
    )

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return self.name


class Variant(db.Model):
    __tablename__ = "variant"
    id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String(30), nullable=False)
    # Price multiplier for this variant (1 = base price).
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    weight = db.Column(db.Float)
    is_default = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(300))
    variant_image = db.Column(db.Unicode(128))
    created_at = db.Column(db.DateTime, index=True, default=utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    products = db.relationship(
        "Product", secondary="variant_product_rel", backref=db.backref("variant", lazy="dynamic")
    )

    def __repr__(self):
        return self.size


class VariantProduct(db.Model):
    __tablename__ = "variant_product_rel"
    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    association_type = db.Column(db.String(30), nullable=True)


# Kinds of related product. The key is stored; the label is what admins see.
ASSOCIATION_TYPES = {
    "XSELL": "Cross-sell: Complete the look",
    "UPSELL": "Upsell: Upgrade to",
}


class ProductAssociation(db.Model):
    """A related product shown on another product's page (and in the bag, for cross-sells)."""

    __tablename__ = "product_association"
    __table_args__ = (
        db.UniqueConstraint(
            "source_product_id", "target_product_id", "association_type", name="uq_product_association"
        ),
    )
    id = db.Column(db.Integer, primary_key=True)
    source_product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    target_product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    association_type = db.Column(db.String(30), nullable=False, default="XSELL")
    position = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    source_product = db.relationship(
        "Product", foreign_keys=[source_product_id], back_populates="associations"
    )
    # Deleting a product also removes links that point at it.
    target_product = db.relationship(
        "Product",
        foreign_keys=[target_product_id],
        backref=db.backref("linked_from", cascade="all, delete-orphan"),
    )

    def __repr__(self):
        return (
            f"{ASSOCIATION_TYPES.get(self.association_type, self.association_type)} → {self.target_product}"
        )


class Attribute(db.Model):
    __tablename__ = "attribute"
    id = db.Column(db.Integer, primary_key=True)
    attribute_name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    attribute_value = db.Column(db.String(300))

    def __repr__(self):
        return self.attribute_name

    def __unicode__(self):
        return self.attribute_name


class ProductAttribute(db.Model):
    __tablename__ = "product_attribute_rel"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    attribute_id = db.Column(db.Integer, db.ForeignKey("attribute.id", ondelete="CASCADE"), nullable=False)
    product = db.relationship("Product", backref="attribute_links")
    attribute = db.relationship("Attribute", backref="product_links")


class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), index=True, unique=True, nullable=False)
    name = db.Column(db.String(64), index=True, nullable=False)
    description = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    # Menu tree: top-level categories are the main menu, their children the dropdown.
    parent_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="SET NULL"), index=True)
    position = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    show_in_menu = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    # Optional rule: also list every active product priced at or below this (e.g. "Under $25").
    max_price = db.Column(db.Numeric(10, 2))
    banner_image = db.Column(db.Unicode(255))
    parent = db.relationship("Category", remote_side=[id], back_populates="children")
    children = db.relationship("Category", back_populates="parent", order_by="Category.position")

    @property
    def slug(self):
        return self.code.lower()

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return self.name


class ProductCategory(db.Model):
    __tablename__ = "category_product_rel"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="CASCADE"), nullable=False)


class Carousel(db.Model):
    """A slide in the home page's top banner: background image, headline and message.

    Every active slide is shown, in position order (Admin > Content > Home banner slides).
    """

    __tablename__ = "carousel"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    header = db.Column(db.String(500), nullable=False)
    text = db.Column(db.Text, nullable=False)
    image = db.Column(db.Unicode(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    position = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at = db.Column(db.DateTime, index=True, default=utcnow)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return self.name

    def __unicode__(self):
        return self.name


class Cart(db.Model):
    __tablename__ = "cart"
    id = db.Column(db.Integer, primary_key=True)
    total_merchandise = db.Column(db.Numeric(10, 2), default=0.00)
    total_shipping = db.Column(db.Numeric(10, 2), default=0.00)
    total_taxes = db.Column(db.Numeric(10, 2), default=0.00)
    total_discount = db.Column(db.Numeric(10, 2), default=0.00)
    total_cart = db.Column(db.Numeric(10, 2), default=0.00)
    status = db.Column(db.String(64), index=True, default="PENDING", nullable=False)
    shipping_method = db.Column(db.String(20))  # a key of services.shipping.METHODS; None = default
    customer_id = db.Column(db.BigInteger, db.ForeignKey("customer.id"), index=True)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)

    customer = db.relationship("Customer")
    items = db.relationship("Item", back_populates="cart", order_by="Item.id", cascade="all, delete-orphan")

    @property
    def pending_items(self):
        return [item for item in self.items if item.status == "PENDING"]


class Item(db.Model):
    __tablename__ = "item"
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    size_id = db.Column(db.Integer, db.ForeignKey("variant.id"))
    product_sku = db.Column(db.String(64), nullable=False)
    product_name = db.Column(db.String(300))
    product_price = db.Column(db.Numeric(10, 2), default=0.00)
    status = db.Column(db.String(64), default="PENDING", nullable=False)
    shipping_base_charge = db.Column(db.Numeric(10, 2), default=0.00)
    shipping_up_charge = db.Column(db.Numeric(10, 2), default=0.00)
    merchandise_tax = db.Column(db.Numeric(10, 2), default=0.00)
    shipping_tax = db.Column(db.Numeric(10, 2), default=0.00)
    merchandise_discount = db.Column(db.Numeric(10, 2), default=0.00)
    shipping_discount = db.Column(db.Numeric(10, 2), default=0.00)
    total_shipping = db.Column(db.Numeric(10, 2), default=0.00)
    total_tax = db.Column(db.Numeric(10, 2), default=0.00)
    total_discount = db.Column(db.Numeric(10, 2), default=0.00)
    total_item = db.Column(db.Numeric(10, 2), default=0.00)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)

    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product")
    variant = db.relationship("Variant", foreign_keys=[size_id])


class Customer(db.Model):
    __tablename__ = "customer"
    id = db.Column(db.BigInteger, primary_key=True)
    customer_type = db.Column(db.String(60), default="GUEST")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    shipping_address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    billing_address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)

    user = db.relationship("User")
    shipping_address = db.relationship("Address", foreign_keys=[shipping_address_id])
    billing_address = db.relationship("Address", foreign_keys=[billing_address_id])


class Address(db.Model):
    __tablename__ = "address"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(200), nullable=False)
    address1 = db.Column(db.String(200), nullable=False)
    address2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(20), default="US")
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    verifiedAddress = db.Column(db.Boolean, default=False)


class Holiday(db.Model):
    __tablename__ = "holiday"
    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.DateTime, index=True)


class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True)
    payment_method = db.Column(db.String(200), nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"))
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), index=True)
    transaction_id = db.Column(db.String(500))
    transaction_status = db.Column(db.String(500))
    auth_code = db.Column(db.String(500))
    requested_amount = db.Column(db.Numeric(10, 2), default=0.00)
    approved_amount = db.Column(db.Numeric(10, 2), default=0.00)
    updated_at = db.Column(db.DateTime, index=True, default=utcnow)
    created_at = db.Column(db.DateTime, index=True, default=utcnow)


# Order lifecycle. A cart becomes an Order when it is paid for; after that the
# cart is history and the order is what customers and admins look at.
ORDER_STATUSES = ("PLACED", "SHIPPED", "DELIVERED", "CANCELLED")


class Order(db.Model):
    """A placed order: a snapshot of the cart, its prices and addresses at checkout."""

    __tablename__ = "orders"  # "order" is a reserved word in SQL
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey("customer.id"), index=True, nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.id"), unique=True)
    status = db.Column(db.String(32), index=True, nullable=False, default="PLACED")
    total_merchandise = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_shipping = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_taxes = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_method = db.Column(db.String(20), nullable=False, default="STANDARD", server_default="STANDARD")
    carrier = db.Column(db.String(20))
    tracking_number = db.Column(db.String(64), index=True)
    # Set when the label was bought through Shippo (the label PDF link expires; refresh via the transaction).
    shippo_transaction_id = db.Column(db.String(64))
    label_url = db.Column(db.String(1000))
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    # Addresses are never edited in place (a change saves a new row), so these
    # keep pointing at the address the order was shipped to.
    shipping_address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    billing_address_id = db.Column(db.Integer, db.ForeignKey("address.id"))
    placed_at = db.Column(db.DateTime, index=True, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    customer = db.relationship("Customer")
    shipping_address = db.relationship("Address", foreign_keys=[shipping_address_id])
    billing_address = db.relationship("Address", foreign_keys=[billing_address_id])
    items = db.relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    payments = db.relationship("Payment", order_by="Payment.id")

    @property
    def number(self):
        return f"BZ-{self.id:06d}"

    @property
    def method(self):
        from app.services.shipping import method_for

        return method_for(self.shipping_method)

    @property
    def estimated_delivery(self):
        """(earliest, latest) dates, counted in business days from when the order was placed."""
        from app.services.shipping import estimated_delivery

        return estimated_delivery(self.shipping_method, self.placed_at.date())

    @property
    def tracking_url(self):
        from app.services.shipping import tracking_url

        return tracking_url(self.carrier, self.tracking_number)

    def __repr__(self):
        return self.number if self.id else "<new order>"


class OrderItem(db.Model):
    """One line of an order. Product details are copied so later catalog edits don't rewrite history."""

    __tablename__ = "order_item"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="SET NULL"))
    variant_id = db.Column(db.Integer, db.ForeignKey("variant.id", ondelete="SET NULL"))
    sku = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(300), nullable=False)
    variant_name = db.Column(db.String(30))
    image = db.Column(db.Unicode(128))
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    order = db.relationship("Order", back_populates="items")

    @property
    def total(self):
        return self.price + self.shipping + self.tax - self.discount
