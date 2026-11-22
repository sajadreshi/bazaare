"""emails and pages: content pages (about, policies) and email addresses in shop settings

The page texts themselves are added by seeding (app/content/pages.py) when the app starts.

Revision ID: c3e8f1a5d7b2
Revises: b7d2e9f4a6c1
Create Date: 2026-11-22 05:00:00

"""

import sqlalchemy as sa
from alembic import op

revision = "c3e8f1a5d7b2"
down_revision = "b7d2e9f4a6c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "page",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.String(length=300), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_slug", "page", ["slug"], unique=True)
    with op.batch_alter_table("shop_settings") as batch_op:
        batch_op.add_column(sa.Column("order_alert_email", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column("support_email", sa.String(length=120), server_default="support@bazaare.com", nullable=True)
        )


def downgrade():
    with op.batch_alter_table("shop_settings") as batch_op:
        batch_op.drop_column("support_email")
        batch_op.drop_column("order_alert_email")
    op.drop_index("ix_page_slug", table_name="page")
    op.drop_table("page")
