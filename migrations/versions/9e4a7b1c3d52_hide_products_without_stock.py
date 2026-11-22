"""hide products that have nothing to sell: options with no stock count can't be sold any more

Products whose options are all uncounted (or at/below the shop threshold) are hidden and
marked sold out, so they come back by themselves once stock is entered.

Revision ID: 9e4a7b1c3d52
Revises: 8d2f4c6a1b37
Create Date: 2026-11-22 00:50:00

"""

import sqlalchemy as sa
from alembic import op

revision = "9e4a7b1c3d52"
down_revision = "8d2f4c6a1b37"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE product SET is_active = false, sold_out_at = CURRENT_TIMESTAMP "
            "WHERE is_active = true "
            "AND EXISTS (SELECT 1 FROM variant v WHERE v.product_id = product.id) "
            "AND NOT EXISTS (SELECT 1 FROM variant v WHERE v.product_id = product.id AND v.stock > "
            "COALESCE((SELECT MIN(s.stock_threshold) FROM shop_settings s), 0))"
        )
    )


def downgrade():
    # Before this, uncounted options sold freely: show the products this hid again.
    op.execute(
        sa.text(
            "UPDATE product SET is_active = true, sold_out_at = NULL "
            "WHERE sold_out_at IS NOT NULL "
            "AND EXISTS (SELECT 1 FROM variant v WHERE v.product_id = product.id AND v.stock IS NULL)"
        )
    )
