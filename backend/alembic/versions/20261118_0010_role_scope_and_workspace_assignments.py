"""role workspace scope and workspace assignments

- roles.workspace_scope: "all" or "assigned". The Client role becomes "assigned".
- workspace_assignments: which workspaces a member with an "assigned" role sees.
- Every client-portal link (client_users) becomes an assignment to that client's workspace.
  client_users is kept, unused, until a later migration removes it.
- Business organizations lose the Client role (they have no clients) when nobody uses it.

New built-in roles (Account Manager, Reporting Viewer) and the new role names are added by the
startup sync (rbac.service.sync_permissions), which already keeps built-in roles current.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-18 00:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('roles', sa.Column('workspace_scope', sa.String(length=20),
                                     server_default='all', nullable=False))
    op.create_check_constraint(op.f('ck_roles_workspace_scope_valid'), 'roles',
                               "workspace_scope IN ('all', 'assigned')")
    op.execute("UPDATE roles SET workspace_scope = 'assigned' WHERE system_key = 'client'")

    op.create_table(
        'workspace_assignments',
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('member_id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['organization_members.id'],
                                name=op.f('fk_workspace_assignments_member_id_organization_members'),
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'],
                                name=op.f('fk_workspace_assignments_organization_id_organizations'),
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'],
                                name=op.f('fk_workspace_assignments_workspace_id_workspaces'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_workspace_assignments')),
        sa.UniqueConstraint('member_id', 'workspace_id',
                            name=op.f('uq_workspace_assignments_member_id')),
    )
    for col in ('organization_id', 'member_id', 'workspace_id'):
        op.create_index(op.f(f'ix_workspace_assignments_{col}'), 'workspace_assignments', [col])

    op.execute("""
        INSERT INTO workspace_assignments (id, organization_id, member_id, workspace_id)
        SELECT gen_random_uuid(), cu.organization_id, m.id, w.id
        FROM client_users cu
        JOIN organization_members m
          ON m.organization_id = cu.organization_id AND m.user_id = cu.user_id
        JOIN workspaces w ON w.client_id = cu.client_id
        ON CONFLICT DO NOTHING
    """)

    op.execute("""
        DELETE FROM roles r USING organizations o
        WHERE r.organization_id = o.id AND o.kind = 'business' AND r.system_key = 'client'
          AND NOT EXISTS (SELECT 1 FROM organization_members m WHERE m.role_id = r.id)
          AND NOT EXISTS (SELECT 1 FROM invitations i WHERE i.role_id = r.id)
    """)


def downgrade() -> None:
    # Assignments made after the upgrade go back into client_users where they map to a
    # client workspace; assignments to own workspaces have no equivalent and are dropped.
    op.execute("""
        INSERT INTO client_users (id, organization_id, client_id, user_id)
        SELECT gen_random_uuid(), a.organization_id, w.client_id, m.user_id
        FROM workspace_assignments a
        JOIN workspaces w ON w.id = a.workspace_id AND w.client_id IS NOT NULL
        JOIN organization_members m ON m.id = a.member_id
        JOIN roles r ON r.id = m.role_id AND r.system_key = 'client'
        WHERE w.organization_id = a.organization_id
        ON CONFLICT DO NOTHING
    """)
    for col in ('workspace_id', 'member_id', 'organization_id'):
        op.drop_index(op.f(f'ix_workspace_assignments_{col}'), table_name='workspace_assignments')
    op.drop_table('workspace_assignments')
    op.drop_constraint(op.f('ck_roles_workspace_scope_valid'), 'roles', type_='check')
    op.drop_column('roles', 'workspace_scope')
