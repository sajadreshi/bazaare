"""product editor: per-product options with price and stock, a photo list, clearer price names

- product.sale_price -> price, product.retail_price -> compare_at_price (empty unless higher);
- product photos move from four fixed columns to product_image (any number, ordered);
- variants belong to one product (variant.product_id) with their own price, stock and position.
  A variant shared by several products is copied once per product, and cart and order lines
  are pointed at their product's copy. The price multiplier becomes an exact price.
- unused columns go: product.display, unit_quantity, is_sustainable; variant.quantity, description.

Revision ID: 5c1e7a9b2d40
Revises: b3f1d6e2c8a4
Create Date: 2026-11-21 20:00:00

"""

from decimal import ROUND_HALF_UP, Decimal

import sqlalchemy as sa
from alembic import op

revision = "5c1e7a9b2d40"
down_revision = "b3f1d6e2c8a4"
branch_labels = None
depends_on = None

IMAGE_COLUMNS = ("main_image", "alt1_image", "alt2_image", "alt3_image")


def _money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def upgrade():
    conn = op.get_bind()

    # ---- photos
    op.create_table(
        "product_image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image", sa.Unicode(length=255), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_image_product_id", "product_image", ["product_id"])
    rows = conn.execute(sa.text(f"SELECT id, {', '.join(IMAGE_COLUMNS)} FROM product ORDER BY id")).all()
    images = sa.table("product_image", sa.column("product_id"), sa.column("image"), sa.column("position"))
    photo_rows = []
    for pid, *keys in rows:
        for position, key in enumerate(k for k in keys if k):
            photo_rows.append({"product_id": pid, "image": key, "position": position})
    if photo_rows:
        op.bulk_insert(images, photo_rows)

    # ---- variants: one product each, exact price, stock, order
    with op.batch_alter_table("variant") as batch_op:
        batch_op.add_column(sa.Column("product_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("price", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("stock", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("position", sa.Integer(), server_default="0", nullable=False))
        batch_op.alter_column(
            "size", new_column_name="name", existing_type=sa.String(30), type_=sa.String(64)
        )
        batch_op.alter_column("variant_image", existing_type=sa.Unicode(128), type_=sa.Unicode(255))

    prices = dict(conn.execute(sa.text("SELECT id, sale_price FROM product")).all())
    variants = {
        row.id: row
        for row in conn.execute(
            sa.text(
                "SELECT id, name, quantity, weight, is_default, variant_image, created_at, updated_at "
                "FROM variant"
            )
        ).all()
    }
    links = conn.execute(
        sa.text("SELECT variant_id, product_id FROM variant_product_rel ORDER BY variant_id, id")
    ).all()
    seen_links = set()
    assigned = set()  # variant rows already given to a product
    position = {}
    labelled = {
        pid
        for (pid,) in conn.execute(
            sa.text(
                "SELECT DISTINCT l.product_id FROM variant_product_rel l "
                "JOIN variant v ON v.id = l.variant_id WHERE v.description = 'Design'"
            )
        ).all()
    }
    for variant_id, product_id in links:
        v = variants.get(variant_id)
        if v is None or product_id not in prices or (variant_id, product_id) in seen_links:
            continue
        seen_links.add((variant_id, product_id))
        multiplier = Decimal(str(v.quantity if v.quantity is not None else 1))
        price = None if multiplier == 1 else _money(Decimal(str(prices[product_id] or 0)) * multiplier)
        pos = position.get(product_id, 0)
        position[product_id] = pos + 1
        values = {"pid": product_id, "price": price, "pos": pos}
        if variant_id not in assigned:
            assigned.add(variant_id)
            conn.execute(
                sa.text(
                    "UPDATE variant SET product_id = :pid, price = :price, position = :pos WHERE id = :vid"
                ),
                {**values, "vid": variant_id},
            )
            continue
        new_id = conn.execute(
            sa.text(
                "INSERT INTO variant (product_id, name, quantity, price, position, weight, is_default, "
                "variant_image, "
                "created_at, updated_at) VALUES (:pid, :name, 1, :price, :pos, :weight, :is_default, :image, "
                ":created_at, :updated_at) RETURNING id"
            ),
            {
                **values,
                "name": v.name,
                "weight": v.weight,
                "is_default": v.is_default,
                "image": v.variant_image,
                "created_at": v.created_at,
                "updated_at": v.updated_at,
            },
        ).scalar_one()
        for table, column in (("item", "size_id"), ("order_item", "variant_id")):
            conn.execute(
                sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old AND product_id = :pid"),
                {"new": new_id, "old": variant_id, "pid": product_id},
            )

    # Variants no product uses any more.
    conn.execute(
        sa.text(
            "UPDATE item SET size_id = NULL "
            "WHERE size_id IN (SELECT id FROM variant WHERE product_id IS NULL)"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE order_item SET variant_id = NULL "
            "WHERE variant_id IN (SELECT id FROM variant WHERE product_id IS NULL)"
        )
    )
    conn.execute(sa.text("DELETE FROM variant WHERE product_id IS NULL"))
    conn.execute(sa.text("UPDATE variant SET is_default = false WHERE is_default IS NULL"))
    op.drop_table("variant_product_rel")

    with op.batch_alter_table("variant") as batch_op:
        batch_op.alter_column("product_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column(
            "is_default", existing_type=sa.Boolean(), nullable=False, server_default=sa.false()
        )
        batch_op.create_foreign_key(
            "variant_product_id_fkey", "product", ["product_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_index("ix_variant_product_id", ["product_id"])
        batch_op.drop_column("quantity")
        batch_op.drop_column("description")

    # Cart lines survive their product or option being deleted.
    with op.batch_alter_table("item") as batch_op:
        batch_op.drop_constraint("item_size_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("item_product_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key("item_size_id_fkey", "variant", ["size_id"], ["id"], ondelete="SET NULL")
        batch_op.create_foreign_key(
            "item_product_id_fkey", "product", ["product_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("order_item") as batch_op:
        batch_op.alter_column("variant_name", existing_type=sa.String(30), type_=sa.String(64))

    # ---- product
    with op.batch_alter_table("product") as batch_op:
        batch_op.alter_column("sale_price", new_column_name="price", existing_type=sa.Numeric(10, 2))
        batch_op.alter_column(
            "retail_price", new_column_name="compare_at_price", existing_type=sa.Numeric(10, 2), nullable=True
        )
        batch_op.alter_column("name", existing_type=sa.String(64), type_=sa.String(150))
        batch_op.alter_column("description", existing_type=sa.String(300), type_=sa.Text())
        batch_op.add_column(sa.Column("option_label", sa.String(30), nullable=True))
        for column in (*IMAGE_COLUMNS, "is_sustainable", "display", "unit_quantity"):
            batch_op.drop_column(column)
    conn.execute(sa.text("UPDATE product SET compare_at_price = NULL WHERE compare_at_price <= price"))
    for pid in labelled:
        conn.execute(sa.text("UPDATE product SET option_label = 'Design' WHERE id = :pid"), {"pid": pid})


def downgrade():
    conn = op.get_bind()

    with op.batch_alter_table("product") as batch_op:
        for column in IMAGE_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.Unicode(128), nullable=True))
        batch_op.add_column(sa.Column("is_sustainable", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("display", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("unit_quantity", sa.Integer(), nullable=True))
        batch_op.drop_column("option_label")
    conn.execute(sa.text("UPDATE product SET compare_at_price = price WHERE compare_at_price IS NULL"))
    conn.execute(sa.text("UPDATE product SET display = is_active"))
    with op.batch_alter_table("product") as batch_op:
        batch_op.alter_column("price", new_column_name="sale_price", existing_type=sa.Numeric(10, 2))
        batch_op.alter_column(
            "compare_at_price",
            new_column_name="retail_price",
            existing_type=sa.Numeric(10, 2),
            nullable=False,
        )
        batch_op.alter_column("name", existing_type=sa.String(150), type_=sa.String(64))
        batch_op.alter_column("description", existing_type=sa.Text(), type_=sa.String(300))

    photos = {}
    for pid, key in conn.execute(
        sa.text("SELECT product_id, image FROM product_image ORDER BY product_id, position, id")
    ).all():
        photos.setdefault(pid, []).append(key)
    for pid, keys in photos.items():
        values = dict(zip(IMAGE_COLUMNS, keys, strict=False))
        sets = ", ".join(f"{column} = :{column}" for column in values)
        conn.execute(sa.text(f"UPDATE product SET {sets} WHERE id = :pid"), {**values, "pid": pid})
    op.drop_index("ix_product_image_product_id", table_name="product_image")
    op.drop_table("product_image")

    with op.batch_alter_table("order_item") as batch_op:
        batch_op.alter_column("variant_name", existing_type=sa.String(64), type_=sa.String(30))
    with op.batch_alter_table("item") as batch_op:
        batch_op.drop_constraint("item_size_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("item_product_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key("item_size_id_fkey", "variant", ["size_id"], ["id"])
        batch_op.create_foreign_key("item_product_id_fkey", "product", ["product_id"], ["id"])

    op.create_table(
        "variant_product_rel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("association_type", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["variant.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    conn.execute(
        sa.text("INSERT INTO variant_product_rel (variant_id, product_id) SELECT id, product_id FROM variant")
    )
    with op.batch_alter_table("variant") as batch_op:
        batch_op.add_column(sa.Column("quantity", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("description", sa.String(300), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE variant SET quantity = COALESCE(ROUND(price / NULLIF("
            "(SELECT p.sale_price FROM product p WHERE p.id = variant.product_id), 0), 2), 1)"
        )
    )
    with op.batch_alter_table("variant") as batch_op:
        batch_op.alter_column("quantity", existing_type=sa.Numeric(10, 2), nullable=False)
        batch_op.drop_index("ix_variant_product_id")
        batch_op.drop_constraint("variant_product_id_fkey", type_="foreignkey")
        batch_op.drop_column("product_id")
        batch_op.drop_column("price")
        batch_op.drop_column("stock")
        batch_op.drop_column("position")
        batch_op.alter_column("is_default", existing_type=sa.Boolean(), nullable=True, server_default=None)
        batch_op.alter_column(
            "name", new_column_name="size", existing_type=sa.String(64), type_=sa.String(30)
        )
        batch_op.alter_column("variant_image", existing_type=sa.Unicode(255), type_=sa.Unicode(128))
