"""platform roles, site settings and product modules

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-15 18:18:56.782108
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('product_modules',
    sa.Column('slug', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('summary', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('available', 'in_development', 'hidden')", name=op.f('ck_product_modules_status_valid')),
    sa.PrimaryKeyConstraint('slug', name=op.f('pk_product_modules'))
    )
    op.create_table('site_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by_user_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint('id = 1', name=op.f('ck_site_settings_single_row')),
    sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], name=op.f('fk_site_settings_updated_by_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_site_settings'))
    )
    op.add_column('users', sa.Column('platform_role', sa.String(length=20), nullable=True))
    op.create_check_constraint(
        'platform_role_valid', 'users',
        "platform_role IS NULL OR platform_role IN ('content_editor', 'site_admin')")

    # The marketing site's product modules, with their status as of Phase 1 (spec §1 of the
    # Phase 1.5 plan). Site admins change statuses as features ship.
    modules = sa.table('product_modules', sa.column('slug'), sa.column('name'),
                       sa.column('summary'), sa.column('status'), sa.column('sort_order'))
    op.bulk_insert(modules, [
        {'slug': 'client-management', 'name': 'Client Management', 'status': 'available', 'sort_order': 10,
         'summary': 'Clients, websites, team roles and client portals in one workspace.'},
        {'slug': 'seo-management', 'name': 'SEO Management', 'status': 'in_development', 'sort_order': 20,
         'summary': 'Technical audits, keywords and search visibility for every site.'},
        {'slug': 'website-analytics', 'name': 'Website Analytics', 'status': 'in_development', 'sort_order': 30,
         'summary': 'Google Analytics 4 and Search Console, side by side.'},
        {'slug': 'social-media-management', 'name': 'Social Media Management', 'status': 'in_development', 'sort_order': 40,
         'summary': 'Plan, schedule and approve posts across your clients’ channels.'},
        {'slug': 'content-marketing', 'name': 'Content Marketing', 'status': 'in_development', 'sort_order': 50,
         'summary': 'Editorial calendars and keyword-to-content planning.'},
        {'slug': 'marketing-analytics', 'name': 'Marketing Analytics', 'status': 'in_development', 'sort_order': 60,
         'summary': 'Channels, campaigns and conversions in one view.'},
        {'slug': 'reporting', 'name': 'Reporting', 'status': 'in_development', 'sort_order': 70,
         'summary': 'Clear client reports with PDF and CSV exports.'},
    ])
    op.execute("INSERT INTO site_settings (id, data) VALUES (1, '{}')")


def downgrade() -> None:
    op.drop_constraint('platform_role_valid', 'users', type_='check')
    op.drop_column('users', 'platform_role')
    op.drop_table('site_settings')
    op.drop_table('product_modules')
