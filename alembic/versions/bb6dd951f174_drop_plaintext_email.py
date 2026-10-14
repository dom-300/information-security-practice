"""drop_plaintext_email

Revision ID: bb6dd951f174
Revises: a589242a55cf
Create Date: 2026-10-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'bb6dd951f174'
down_revision: Union[str, None] = 'a589242a55cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_email")
        batch.drop_column("email")

def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email", sa.String(100), nullable=True))
