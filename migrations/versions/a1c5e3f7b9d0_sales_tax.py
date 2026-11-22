"""sales tax: states the shop collects in, ZIP rate table, and the tax charged on carts and orders

New York is set up to collect (shipping is taxable there), with 8.625% (Nassau/Suffolk)
as the rate for any ZIP not yet in the rate table.

Revision ID: a1c5e3f7b9d0
Revises: 9e4a7b1c3d52
Create Date: 2026-11-22 01:10:00

"""

import sqlalchemy as sa
from alembic import op

revision = "a1c5e3f7b9d0"
down_revision = "9e4a7b1c3d52"
branch_labels = None
depends_on = None


def upgrade():
    states = op.create_table(
        "tax_state",
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("collect", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("tax_shipping", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("fallback_rate", sa.Numeric(7, 6), server_default="0", nullable=False),
        sa.Column("rates_updated_at", sa.DateTime(), nullable=True),
        sa.Column("rates_source", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("state"),
    )
    op.bulk_insert(states, [{"state": "NY", "collect": True, "tax_shipping": True, "fallback_rate": 0.08625}])
    op.create_table(
        "tax_rate",
        sa.Column("zip", sa.String(length=5), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("rate", sa.Numeric(7, 6), nullable=False),
        sa.Column("state_rate", sa.Numeric(7, 6), nullable=True),
        sa.Column("county_rate", sa.Numeric(7, 6), nullable=True),
        sa.Column("city_rate", sa.Numeric(7, 6), nullable=True),
        sa.Column("special_rate", sa.Numeric(7, 6), nullable=True),
        sa.PrimaryKeyConstraint("zip"),
    )
    op.create_index("ix_tax_rate_state", "tax_rate", ["state"])
    with op.batch_alter_table("cart") as batch_op:
        batch_op.add_column(sa.Column("tax_rate", sa.Numeric(7, 6), nullable=True))
        batch_op.add_column(sa.Column("tax_region", sa.String(length=120), nullable=True))
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("tax_state", sa.String(length=2), nullable=True))
        batch_op.add_column(sa.Column("tax_rate", sa.Numeric(7, 6), nullable=True))
        batch_op.add_column(sa.Column("tax_region", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("shipping_tax", sa.Numeric(10, 2), server_default="0", nullable=False))
    op.create_index("ix_orders_tax_state", "orders", ["tax_state"])


def downgrade():
    op.drop_index("ix_orders_tax_state", table_name="orders")
    with op.batch_alter_table("orders") as batch_op:
        for column in ("shipping_tax", "tax_region", "tax_rate", "tax_state"):
            batch_op.drop_column(column)
    with op.batch_alter_table("cart") as batch_op:
        batch_op.drop_column("tax_region")
        batch_op.drop_column("tax_rate")
    op.drop_index("ix_tax_rate_state", table_name="tax_rate")
    op.drop_table("tax_rate")
    op.drop_table("tax_state")
