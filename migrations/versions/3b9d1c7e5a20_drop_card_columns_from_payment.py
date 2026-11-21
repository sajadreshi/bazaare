"""drop card data columns from payment

Card numbers, cardholder names and expiry dates must never be stored by the
shop (PCI DSS). A payment gateway keeps them; we keep its transaction id and
auth code. Downgrade restores the empty columns only; the data is gone.

Revision ID: 3b9d1c7e5a20
Revises: f2a63e830181
Create Date: 2026-11-21 02:10:00

"""

import sqlalchemy as sa
from alembic import op

revision = "3b9d1c7e5a20"
down_revision = "f2a63e830181"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payment") as batch_op:
        batch_op.drop_column("account_number")
        batch_op.drop_column("account_name")
        batch_op.drop_column("expiry_month")
        batch_op.drop_column("expiry_year")


def downgrade():
    with op.batch_alter_table("payment") as batch_op:
        batch_op.add_column(sa.Column("expiry_year", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("expiry_month", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("account_name", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("account_number", sa.String(length=500), nullable=True))
