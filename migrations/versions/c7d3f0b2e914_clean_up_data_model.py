"""clean up the data model: one link per relationship, fixed names, unused tables

- product.variant_id, category.product_id, collection.category_id and
  home_content.carousal_id duplicated the many-to-many link tables
  (variant_product_rel, category_product_rel, collection_category_rel,
  home_carousal_rel). Any link only stored in the old column is copied into
  the link table first, then the column is dropped.
- carousal -> carousel, home_carousal_rel -> home_carousel_rel,
  user.marketting_* -> user.marketing_*.
- item_attr / item_attr_rel were never used by the app and are dropped.

Revision ID: c7d3f0b2e914
Revises: a4c2e9d81f00
Create Date: 2026-11-21 02:25:00

"""

import sqlalchemy as sa
from alembic import op

revision = "c7d3f0b2e914"
down_revision = "a4c2e9d81f00"
branch_labels = None
depends_on = None

# (table, old column, its FK constraint, link table, link cols (this side, other side), referenced table)
DUPLICATE_LINKS = [
    ("product", "variant_id", "product_variant_id_fkey", "variant_product_rel", ("product_id", "variant_id"), "variant"),
    ("category", "product_id", "category_product_id_fkey", "category_product_rel", ("category_id", "product_id"), "product"),
    ("collection", "category_id", "collection_category_id_fkey", "collection_category_rel", ("collection_id", "category_id"), "category"),
    ("home_content", "carousal_id", "home_content_carousal_id_fkey", "home_carousal_rel", ("home_content_id", "carousal_id"), "carousal"),
]


def _is_postgres():
    return op.get_bind().dialect.name == "postgresql"


def upgrade():
    for table, column, fk, link, (this_col, other_col), _ in DUPLICATE_LINKS:
        op.execute(
            f"""
            INSERT INTO {link} ({this_col}, {other_col})
            SELECT t.id, t.{column} FROM {table} t
            WHERE t.{column} IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM {link} l
                              WHERE l.{this_col} = t.id AND l.{other_col} = t.{column})
            """
        )
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(fk, type_="foreignkey")
            batch_op.drop_column(column)

    op.rename_table("carousal", "carousel")
    op.rename_table("home_carousal_rel", "home_carousel_rel")
    with op.batch_alter_table("home_carousel_rel") as batch_op:
        batch_op.alter_column("carousal_id", new_column_name="carousel_id")
    if _is_postgres():
        for old, new in [
            ("ix_carousal_created_at", "ix_carousel_created_at"),
            ("ix_carousal_updated_at", "ix_carousel_updated_at"),
        ]:
            op.execute(f"ALTER INDEX {old} RENAME TO {new}")
        op.execute("ALTER SEQUENCE carousal_id_seq RENAME TO carousel_id_seq")
        op.execute("ALTER SEQUENCE home_carousal_rel_id_seq RENAME TO home_carousel_rel_id_seq")
        op.execute("ALTER TABLE carousel RENAME CONSTRAINT carousal_pkey TO carousel_pkey")
        op.execute("ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousal_rel_pkey TO home_carousel_rel_pkey")
        op.execute(
            "ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousal_rel_carousal_id_fkey "
            "TO home_carousel_rel_carousel_id_fkey"
        )
        op.execute(
            "ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousal_rel_home_content_id_fkey "
            "TO home_carousel_rel_home_content_id_fkey"
        )

    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("marketting_email", new_column_name="marketing_email")
        batch_op.alter_column("marketting_sms", new_column_name="marketing_sms")

    op.drop_table("item_attr_rel")
    op.drop_index("ix_item_attr_attr_name", table_name="item_attr")
    op.drop_table("item_attr")


def downgrade():
    op.create_table(
        "item_attr",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attr_name", sa.String(length=64), nullable=False),
        sa.Column("attr_value", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_attr_attr_name", "item_attr", ["attr_name"], unique=True)
    op.create_table(
        "item_attr_rel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_id"], ["item_attr.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("marketing_email", new_column_name="marketting_email")
        batch_op.alter_column("marketing_sms", new_column_name="marketting_sms")

    if _is_postgres():
        op.execute(
            "ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousel_rel_home_content_id_fkey "
            "TO home_carousal_rel_home_content_id_fkey"
        )
        op.execute(
            "ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousel_rel_carousel_id_fkey "
            "TO home_carousal_rel_carousal_id_fkey"
        )
        op.execute("ALTER TABLE home_carousel_rel RENAME CONSTRAINT home_carousel_rel_pkey TO home_carousal_rel_pkey")
        op.execute("ALTER TABLE carousel RENAME CONSTRAINT carousel_pkey TO carousal_pkey")
        op.execute("ALTER SEQUENCE home_carousel_rel_id_seq RENAME TO home_carousal_rel_id_seq")
        op.execute("ALTER SEQUENCE carousel_id_seq RENAME TO carousal_id_seq")
        op.execute("ALTER INDEX ix_carousel_updated_at RENAME TO ix_carousal_updated_at")
        op.execute("ALTER INDEX ix_carousel_created_at RENAME TO ix_carousal_created_at")
    with op.batch_alter_table("home_carousel_rel") as batch_op:
        batch_op.alter_column("carousel_id", new_column_name="carousal_id")
    op.rename_table("home_carousel_rel", "home_carousal_rel")
    op.rename_table("carousel", "carousal")

    # The old columns come back empty: the links live on in the link tables.
    for table, column, fk, _, _, referenced in reversed(DUPLICATE_LINKS):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column(column, sa.Integer(), nullable=True))
            batch_op.create_foreign_key(fk, referenced, [column], ["id"])
