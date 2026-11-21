"""add orders and order_item; backfill from paid carts

Orders used to be carts with status COMPLETED. They now get their own tables,
holding a snapshot of prices, product names and addresses at checkout.
Existing paid carts are copied into orders keeping the same id, so order
numbers customers have already seen don't change.

Revision ID: a4c2e9d81f00
Revises: 3b9d1c7e5a20
Create Date: 2026-11-21 02:20:00

"""

import sqlalchemy as sa
from alembic import op

revision = "a4c2e9d81f00"
down_revision = "3b9d1c7e5a20"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(precision=10, scale=2)


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("cart_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_merchandise", MONEY, nullable=False),
        sa.Column("total_shipping", MONEY, nullable=False),
        sa.Column("total_taxes", MONEY, nullable=False),
        sa.Column("total_discount", MONEY, nullable=False),
        sa.Column("total", MONEY, nullable=False),
        sa.Column("delivery_date", sa.DateTime(), nullable=True),
        sa.Column("delivery_window", sa.String(length=64), nullable=True),
        sa.Column("shipping_address_id", sa.Integer(), nullable=True),
        sa.Column("billing_address_id", sa.Integer(), nullable=True),
        sa.Column("placed_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["billing_address_id"], ["address.id"]),
        sa.ForeignKeyConstraint(["cart_id"], ["cart.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"]),
        sa.ForeignKeyConstraint(["shipping_address_id"], ["address.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_placed_at", "orders", ["placed_at"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table(
        "order_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("variant_name", sa.String(length=30), nullable=True),
        sa.Column("image", sa.Unicode(length=128), nullable=True),
        sa.Column("price", MONEY, nullable=False),
        sa.Column("shipping", MONEY, nullable=False),
        sa.Column("tax", MONEY, nullable=False),
        sa.Column("discount", MONEY, nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["variant.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_item_order_id", "order_item", ["order_id"])
    with op.batch_alter_table("payment") as batch_op:
        batch_op.add_column(sa.Column("order_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_payment_order_id", ["order_id"])
        batch_op.create_foreign_key("payment_order_id_fkey", "orders", ["order_id"], ["id"])

    # Backfill: every cart with an approved payment becomes an order (same id).
    op.execute(
        """
        INSERT INTO orders (id, customer_id, cart_id, status, total_merchandise, total_shipping,
                            total_taxes, total_discount, total, delivery_date, delivery_window,
                            shipping_address_id, billing_address_id, placed_at, updated_at)
        SELECT c.id, c.customer_id, c.id,
               CASE c.status WHEN 'DELIVERED' THEN 'DELIVERED'
                             WHEN 'CANCELLED' THEN 'CANCELLED'
                             ELSE 'PLACED' END,
               COALESCE(c.total_merchandise, 0), COALESCE(c.total_shipping, 0),
               COALESCE(c.total_taxes, 0), COALESCE(c.total_discount, 0), COALESCE(c.total_cart, 0),
               c.delivery_date, c.delivery_window,
               cu.shipping_address_id, cu.billing_address_id,
               COALESCE(c.updated_at, c.created_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP
        FROM cart c
        JOIN customer cu ON cu.id = c.customer_id
        WHERE EXISTS (SELECT 1 FROM payment p
                      WHERE p.cart_id = c.id AND p.transaction_status = 'APPROVED')
        """
    )
    op.execute(
        """
        INSERT INTO order_item (order_id, product_id, variant_id, sku, name, variant_name, image,
                                price, shipping, tax, discount)
        SELECT i.cart_id, i.product_id, i.size_id, i.product_sku,
               COALESCE(i.product_name, p.name, i.product_sku), v.size, p.main_image,
               COALESCE(i.product_price, 0), COALESCE(i.total_shipping, 0),
               COALESCE(i.total_tax, 0), COALESCE(i.total_discount, 0)
        FROM item i
        JOIN orders o ON o.id = i.cart_id
        LEFT JOIN product p ON p.id = i.product_id
        LEFT JOIN variant v ON v.id = i.size_id
        ORDER BY i.id
        """
    )
    op.execute("UPDATE payment SET order_id = cart_id WHERE cart_id IN (SELECT id FROM orders)")
    if op.get_bind().dialect.name == "postgresql":
        # Rows were inserted with explicit ids; move the sequence past them.
        op.execute("SELECT setval('orders_id_seq', (SELECT COALESCE(MAX(id), 0) + 1 FROM orders), false)")


def downgrade():
    # Carts, items and payments still hold everything; only the order copies go.
    with op.batch_alter_table("payment") as batch_op:
        batch_op.drop_constraint("payment_order_id_fkey", type_="foreignkey")
        batch_op.drop_index("ix_payment_order_id")
        batch_op.drop_column("order_id")
    op.drop_index("ix_order_item_order_id", table_name="order_item")
    op.drop_table("order_item")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_placed_at", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
