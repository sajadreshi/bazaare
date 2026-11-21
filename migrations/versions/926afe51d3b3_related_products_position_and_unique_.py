"""related products: position, one link per type, tidy association types

Adds an ordering position, normalises free-text association types
(e.g. "xsell", "Cross-sell" -> XSELL; "up-sell" -> UPSELL), removes exact
duplicates, then makes (source, target, type) unique.

Revision ID: 926afe51d3b3
Revises: d5e8a1c4b7f2
Create Date: 2026-11-21 13:15:03.469577

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '926afe51d3b3'
down_revision = 'd5e8a1c4b7f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product_association") as batch_op:
        batch_op.add_column(sa.Column("position", sa.Integer(), server_default="0", nullable=False))

    op.execute("UPDATE product_association SET association_type = UPPER(TRIM(association_type))")
    op.execute(
        "UPDATE product_association SET association_type = 'XSELL' "
        "WHERE association_type IN ('CROSS-SELL', 'CROSSSELL', 'CROSS SELL', 'X-SELL')"
    )
    op.execute(
        "UPDATE product_association SET association_type = 'UPSELL' WHERE association_type IN ('UP-SELL', 'UP SELL')"
    )
    op.execute(
        """
        DELETE FROM product_association a
        USING product_association b
        WHERE a.id > b.id
          AND a.source_product_id = b.source_product_id
          AND a.target_product_id = b.target_product_id
          AND a.association_type = b.association_type
        """
        if op.get_bind().dialect.name == "postgresql"
        else """
        DELETE FROM product_association WHERE id NOT IN (
            SELECT MIN(id) FROM product_association
            GROUP BY source_product_id, target_product_id, association_type)
        """
    )
    with op.batch_alter_table("product_association") as batch_op:
        batch_op.create_unique_constraint(
            "uq_product_association", ["source_product_id", "target_product_id", "association_type"]
        )


def downgrade():
    with op.batch_alter_table("product_association") as batch_op:
        batch_op.drop_constraint("uq_product_association", type_="unique")
        batch_op.drop_column("position")
