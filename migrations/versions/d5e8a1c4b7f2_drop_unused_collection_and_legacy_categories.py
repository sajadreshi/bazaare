"""drop the unused Collection model and the hidden legacy categories

- collection / collection_category_rel came from the food site and are no
  longer used by the shop (the menu is the category tree); home_content's
  collection_id goes with them.
- RINGS, NECKLACES and BRACELETS were the first jewellery seed, hidden from
  the menu since the category tree replaced them (Accessories > Rings,
  Neckpieces > Necklaces, Accessories > Bangles). Their product links are
  removed with them; the products themselves are untouched.

Downgrade recreates the empty collection tables and column; the legacy
categories are not restored.

Revision ID: d5e8a1c4b7f2
Revises: c43d13f8344e
Create Date: 2026-11-21 18:20:00

"""

import sqlalchemy as sa
from alembic import op

revision = "d5e8a1c4b7f2"
down_revision = "c43d13f8344e"
branch_labels = None
depends_on = None

LEGACY = "('RINGS', 'NECKLACES', 'BRACELETS')"


def upgrade():
    op.drop_table("collection_category_rel")
    with op.batch_alter_table("home_content") as batch_op:
        batch_op.drop_constraint("home_content_collection_id_fkey", type_="foreignkey")
        batch_op.drop_column("collection_id")
    op.drop_index("ix_collection_name", table_name="collection")
    op.drop_index("ix_collection_created_at", table_name="collection")
    op.drop_index("ix_collection_updated_at", table_name="collection")
    op.drop_table("collection")

    legacy = f"SELECT id FROM category WHERE code IN {LEGACY}"
    op.execute(f"DELETE FROM category_product_rel WHERE category_id IN ({legacy})")
    op.execute(f"UPDATE home_content SET category_id = NULL WHERE category_id IN ({legacy})")
    op.execute(f"UPDATE category SET parent_id = NULL WHERE parent_id IN ({legacy})")
    op.execute(f"DELETE FROM category WHERE code IN {LEGACY}")


def downgrade():
    op.create_table(
        "collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collection_name", "collection", ["name"])
    op.create_index("ix_collection_created_at", "collection", ["created_at"])
    op.create_index("ix_collection_updated_at", "collection", ["updated_at"])
    op.create_table(
        "collection_category_rel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_id"], ["collection.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("home_content") as batch_op:
        batch_op.add_column(sa.Column("collection_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("home_content_collection_id_fkey", "collection", ["collection_id"], ["id"])
