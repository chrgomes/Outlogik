"""remove the social approvals portal feature

Social media management stays a separate product (Sociola), so the client portal won't get
social approvals. The website stops listing it. Downgrade puts the row back as it was seeded.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-18 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM portal_features WHERE slug = 'social-approvals'")


def downgrade() -> None:
    features = sa.table('portal_features', sa.column('slug'), sa.column('name'),
                        sa.column('summary'), sa.column('status'), sa.column('sort_order'))
    op.bulk_insert(features, [
        {'slug': 'social-approvals', 'name': 'Social calendar approvals',
         'status': 'in_development', 'sort_order': 60,
         'summary': 'Review and approve social posts before they go out.'},
    ])
