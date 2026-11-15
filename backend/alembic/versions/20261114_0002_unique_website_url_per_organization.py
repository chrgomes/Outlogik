"""unique website url per organization

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14 11:29:25.878630
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint('uq_websites_organization_id_url', 'websites', ['organization_id', 'url'])


def downgrade() -> None:
    op.drop_constraint('uq_websites_organization_id_url', 'websites', type_='unique')
