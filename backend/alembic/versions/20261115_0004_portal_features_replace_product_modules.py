"""portal features replace product modules

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15 18:47:15.428194
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('portal_features',
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('summary', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('available', 'in_development', 'hidden')", name=op.f('ck_portal_features_status_valid')),
    sa.PrimaryKeyConstraint('slug', name=op.f('pk_portal_features'))
    )
    op.drop_table('product_modules')

    # Client-portal features shown on the website ("How we work"). Only what the app does today
    # is available. Site admins change statuses as features ship.
    features = sa.table('portal_features', sa.column('slug'), sa.column('name'),
                        sa.column('summary'), sa.column('status'), sa.column('sort_order'))
    op.bulk_insert(features, [
        {'slug': 'client-portal', 'name': 'Your own client portal', 'status': 'available', 'sort_order': 10,
         'summary': 'A private sign-in for your business, separate from every other client.'},
        {'slug': 'websites-overview', 'name': 'Your websites in one place', 'status': 'available', 'sort_order': 20,
         'summary': 'Every website we look after for you, with its status.'},
        {'slug': 'activity-history', 'name': 'A record of the work', 'status': 'available', 'sort_order': 30,
         'summary': 'Changes to your account and websites, with who made them and when.'},
        {'slug': 'monthly-reports', 'name': 'Monthly reports', 'status': 'in_development', 'sort_order': 40,
         'summary': 'Your monthly results, ready to read online or download as PDF.'},
        {'slug': 'analytics-dashboards', 'name': 'Analytics dashboards', 'status': 'in_development', 'sort_order': 50,
         'summary': 'Traffic and search performance from Google Analytics and Search Console.'},
        {'slug': 'social-approvals', 'name': 'Social calendar approvals', 'status': 'in_development', 'sort_order': 60,
         'summary': 'Review and approve social posts before they go out.'},
        {'slug': 'seo-health', 'name': 'SEO health checks', 'status': 'in_development', 'sort_order': 70,
         'summary': 'Technical issues found on your sites, and when they were fixed.'},
    ])
    # Settings from the software-product direction that no longer exist.
    op.execute("UPDATE site_settings SET data = data - 'early_access' - 'primary_cta_label' - 'demo_cta_label'")


def downgrade() -> None:
    # Restores the empty product_modules table only; its rows aren't recreated.
    op.create_table('product_modules',
    sa.Column('slug', sa.VARCHAR(length=60), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
    sa.Column('summary', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('sort_order', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.CheckConstraint("status::text = ANY (ARRAY['available'::character varying, 'in_development'::character varying, 'hidden'::character varying]::text[])", name=op.f('ck_product_modules_status_valid')),
    sa.PrimaryKeyConstraint('slug', name=op.f('pk_product_modules'))
    )
    op.drop_table('portal_features')
