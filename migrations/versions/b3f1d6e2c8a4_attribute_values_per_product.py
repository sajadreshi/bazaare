"""attribute values per product: an attribute is a type (Stone, Metal...), each product sets its value

Before, attribute rows carried both name and value with a unique name, so
"Stone = Moonstone" could exist but "Stone = Ruby" could not. Now:
- attribute.attribute_name -> attribute.name (still unique), plus an order position;
- product_attribute_rel gets the value (copied from the old attribute value),
  and one value per product per attribute.

Revision ID: b3f1d6e2c8a4
Revises: 4a258060e1eb
Create Date: 2026-11-21 19:20:00

"""

import sqlalchemy as sa
from alembic import op

revision = "b3f1d6e2c8a4"
down_revision = "4a258060e1eb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product_attribute_rel") as batch_op:
        batch_op.add_column(sa.Column("value", sa.String(length=300), nullable=True))
    op.execute(
        "UPDATE product_attribute_rel SET value = "
        "(SELECT COALESCE(a.attribute_value, '') FROM attribute a WHERE a.id = product_attribute_rel.attribute_id)"
    )
    op.execute("UPDATE product_attribute_rel SET value = '' WHERE value IS NULL")
    op.execute(
        "DELETE FROM product_attribute_rel WHERE id NOT IN ("
        "SELECT MIN(id) FROM product_attribute_rel GROUP BY product_id, attribute_id)"
    )
    with op.batch_alter_table("product_attribute_rel") as batch_op:
        batch_op.alter_column("value", existing_type=sa.String(length=300), nullable=False)
        batch_op.create_unique_constraint("uq_product_attribute", ["product_id", "attribute_id"])

    op.drop_index("ix_attribute_attribute_name", table_name="attribute")
    with op.batch_alter_table("attribute") as batch_op:
        batch_op.alter_column("attribute_name", new_column_name="name", existing_type=sa.String(length=64))
        batch_op.add_column(sa.Column("position", sa.Integer(), server_default="0", nullable=False))
        batch_op.drop_column("attribute_value")
    op.create_index("ix_attribute_name", "attribute", ["name"], unique=True)


def downgrade():
    op.drop_index("ix_attribute_name", table_name="attribute")
    with op.batch_alter_table("attribute") as batch_op:
        batch_op.add_column(sa.Column("attribute_value", sa.String(length=300), nullable=True))
        batch_op.drop_column("position")
        batch_op.alter_column("name", new_column_name="attribute_name", existing_type=sa.String(length=64))
    op.create_index("ix_attribute_attribute_name", "attribute", ["attribute_name"], unique=True)
    # The old shape holds one value per attribute: keep the first product's value.
    op.execute(
        "UPDATE attribute SET attribute_value = (SELECT l.value FROM product_attribute_rel l "
        "WHERE l.attribute_id = attribute.id ORDER BY l.id LIMIT 1)"
    )
    with op.batch_alter_table("product_attribute_rel") as batch_op:
        batch_op.drop_constraint("uq_product_attribute", type_="unique")
        batch_op.drop_column("value")
