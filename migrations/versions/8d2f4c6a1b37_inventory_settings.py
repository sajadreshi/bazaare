"""inventory: shop settings (stock threshold, low-stock alert) and products hidden when sold out

Revision ID: 8d2f4c6a1b37
Revises: 5c1e7a9b2d40
Create Date: 2026-11-22 00:40:00

"""

import sqlalchemy as sa
from alembic import op

revision = "8d2f4c6a1b37"
down_revision = "5c1e7a9b2d40"
branch_labels = None
depends_on = None


def upgrade():
    settings = op.create_table(
        "shop_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_threshold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("low_stock_alert", sa.Integer(), server_default="3", nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(settings, [{"id": 1, "stock_threshold": 0, "low_stock_alert": 3}])
    with op.batch_alter_table("product") as batch_op:
        batch_op.add_column(sa.Column("sold_out_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("product") as batch_op:
        batch_op.drop_column("sold_out_at")
    op.drop_table("shop_settings")
