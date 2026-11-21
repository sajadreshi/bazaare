"""home banner slides replace Home Page Content

Each carousel slide gets its own background image, an active flag and an
order, and every active slide is shown on the home page. The separate
home_content screen (one image + chosen slides + a featured category) and its
link table are removed.

Data carried over: slides linked to the newest active home_content stay
active, in their previous order, and take its banner image if they have none;
other slides start inactive (they weren't on the home page before).

Revision ID: e7b2c9d4a1f3
Revises: 926afe51d3b3
Create Date: 2026-11-21 18:45:00

"""

import sqlalchemy as sa
from alembic import op

revision = "e7b2c9d4a1f3"
down_revision = "926afe51d3b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("carousel") as batch_op:
        batch_op.add_column(sa.Column("image", sa.Unicode(length=255), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("position", sa.Integer(), server_default="0", nullable=False))

    bind = op.get_bind()
    home = bind.execute(
        sa.text("SELECT id, hero_image FROM home_content WHERE is_active ORDER BY id DESC LIMIT 1")
    ).first()
    if home is not None:
        slide_ids = [
            row.carousel_id
            for row in bind.execute(
                sa.text("SELECT carousel_id FROM home_carousel_rel WHERE home_content_id = :h ORDER BY carousel_id"),
                {"h": home.id},
            )
        ]
        for position, slide_id in enumerate(slide_ids, start=1):
            bind.execute(
                sa.text(
                    "UPDATE carousel SET is_active = true, position = :p, image = COALESCE(image, :img) WHERE id = :id"
                ),
                {"p": position, "img": home.hero_image, "id": slide_id},
            )

    with op.batch_alter_table("carousel") as batch_op:
        batch_op.alter_column("is_active", server_default=sa.true())
    op.drop_table("home_carousel_rel")
    op.drop_index("ix_home_content_created_at", table_name="home_content")
    op.drop_index("ix_home_content_updated_at", table_name="home_content")
    op.drop_table("home_content")


def downgrade():
    op.create_table(
        "home_content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hero_image", sa.Unicode(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], name="home_content_category_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_home_content_created_at", "home_content", ["created_at"])
    op.create_index("ix_home_content_updated_at", "home_content", ["updated_at"])
    op.create_table(
        "home_carousel_rel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("home_content_id", sa.Integer(), nullable=False),
        sa.Column("carousel_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["carousel_id"], ["carousel.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_content_id"], ["home_content.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("carousel") as batch_op:
        batch_op.drop_column("position")
        batch_op.drop_column("is_active")
        batch_op.drop_column("image")
