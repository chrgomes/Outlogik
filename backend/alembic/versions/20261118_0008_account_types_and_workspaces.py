"""account types and workspaces

Adds organizations.kind, the workspaces table and websites.workspace_id, and moves the
existing data across (docs/HYBRID_SAAS_PLAN.md §2):

- every existing organization becomes an agency and gets an "own" workspace
- every existing client gets a "client" workspace
- every website is placed in its client's workspace

Nothing is deleted. websites.client_id stays, now nullable (websites in an own workspace
have no client).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('kind', sa.String(length=20),
                                             server_default='agency', nullable=False))
    op.create_check_constraint(op.f('ck_organizations_kind_valid'), 'organizations',
                               "kind IN ('business', 'agency')")

    op.create_table(
        'workspaces',
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('client_id', sa.Uuid(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.CheckConstraint("kind IN ('own', 'client')", name=op.f('ck_workspaces_kind_valid')),
        sa.CheckConstraint("(kind = 'client') = (client_id IS NOT NULL)",
                           name=op.f('ck_workspaces_client_matches_kind')),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'],
                                name=op.f('fk_workspaces_client_id_clients'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name=op.f('fk_workspaces_organization_id_organizations'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_workspaces')),
        sa.UniqueConstraint('client_id', name=op.f('uq_workspaces_client_id')),
    )
    op.create_index(op.f('ix_workspaces_organization_id'), 'workspaces', ['organization_id'])
    op.create_index('uq_workspaces_one_own_per_organization', 'workspaces', ['organization_id'],
                    unique=True, postgresql_where=sa.text("kind = 'own'"))

    # Existing data: an own workspace per organization, a client workspace per client.
    op.execute("""
        INSERT INTO workspaces (id, organization_id, kind, name, client_id)
        SELECT gen_random_uuid(), id, 'own', name, NULL FROM organizations
    """)
    op.execute("""
        INSERT INTO workspaces (id, organization_id, kind, name, client_id)
        SELECT gen_random_uuid(), organization_id, 'client', name, id FROM clients
    """)

    op.add_column('websites', sa.Column('workspace_id', sa.Uuid(), nullable=True))
    op.execute("""
        UPDATE websites SET workspace_id = w.id
        FROM workspaces w WHERE w.client_id = websites.client_id
    """)
    op.alter_column('websites', 'workspace_id', nullable=False)
    op.create_index(op.f('ix_websites_workspace_id'), 'websites', ['workspace_id'])
    op.create_foreign_key(op.f('fk_websites_workspace_id_workspaces'), 'websites', 'workspaces',
                          ['workspace_id'], ['id'], ondelete='CASCADE')
    op.alter_column('websites', 'client_id', existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    # Websites in an own workspace have no client, and the old schema can't hold them.
    # Refuse rather than delete them.
    conn = op.get_bind()
    orphaned = conn.scalar(sa.text("SELECT count(*) FROM websites WHERE client_id IS NULL"))
    if orphaned:
        raise RuntimeError(
            f"{orphaned} website(s) belong to an own workspace and have no client. Move or "
            "delete them before downgrading past 0008.")
    op.alter_column('websites', 'client_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint(op.f('fk_websites_workspace_id_workspaces'), 'websites',
                       type_='foreignkey')
    op.drop_index(op.f('ix_websites_workspace_id'), table_name='websites')
    op.drop_column('websites', 'workspace_id')
    op.drop_index('uq_workspaces_one_own_per_organization', table_name='workspaces',
                  postgresql_where=sa.text("kind = 'own'"))
    op.drop_index(op.f('ix_workspaces_organization_id'), table_name='workspaces')
    op.drop_table('workspaces')
    op.drop_constraint(op.f('ck_organizations_kind_valid'), 'organizations', type_='check')
    op.drop_column('organizations', 'kind')
