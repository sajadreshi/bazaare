"""promotions: coupon codes, free-shipping amount and coupon box switch in shop settings

Revision ID: b7d2e9f4a6c1
Revises: a1c5e3f7b9d0
Create Date: 2026-11-22 01:30:00

"""

import sqlalchemy as sa
from alembic import op

revision = "b7d2e9f4a6c1"
down_revision = "a1c5e3f7b9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "coupon",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("min_order", sa.Numeric(10, 2), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("times_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coupon_code", "coupon", ["code"], unique=True)
    with op.batch_alter_table("shop_settings") as batch_op:
        # Standard shipping was free over $50 (hard-coded); now a setting with the same default.
        batch_op.add_column(sa.Column("free_shipping_over", sa.Numeric(10, 2), server_default="50", nullable=True))
        batch_op.add_column(sa.Column("coupons_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    with op.batch_alter_table("cart") as batch_op:
        batch_op.add_column(sa.Column("coupon_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("cart_coupon_id_fkey", "coupon", ["coupon_id"], ["id"], ondelete="SET NULL")
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("coupon_code", sa.String(length=40), nullable=True))


def downgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("coupon_code")
    with op.batch_alter_table("cart") as batch_op:
        batch_op.drop_constraint("cart_coupon_id_fkey", type_="foreignkey")
        batch_op.drop_column("coupon_id")
    with op.batch_alter_table("shop_settings") as batch_op:
        batch_op.drop_column("coupons_enabled")
        batch_op.drop_column("free_shipping_over")
    op.drop_index("ix_coupon_code", table_name="coupon")
    op.drop_table("coupon")
