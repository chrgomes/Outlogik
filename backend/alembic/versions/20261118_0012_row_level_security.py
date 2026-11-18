"""row-level security on tenant tables

A second line of defence behind the application's own checks. For a request inside an
organization, the app sets two transaction settings (app/core/db.py):

- app.org_id: the organization the request is for
- app.linked_ws: workspaces of other organizations shared with it (access grants)

The policies then hide every row of another organization, even if a query forgets its
organization filter. Outside an organization request (sign-in, the public site, the CLI,
migrations) the settings are empty and the policies allow everything, as before.

FORCE applies the policies to the table owner too (the app's own database user). Superusers
and roles with BYPASSRLS are never subject to row-level security, so production must connect
as an ordinary user (docs/DEPLOYMENT.md); the app logs a warning at startup otherwise.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-18 00:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT = "app_tenant()"
UNSET = f"{TENANT} IS NULL"

# table → condition a row must meet inside an organization request
POLICIES = {
    "organization_members": f"organization_id = {TENANT}",
    "roles": f"organization_id = {TENANT}",
    "invitations": f"organization_id = {TENANT}",
    "clients": f"organization_id = {TENANT}",
    "client_users": f"organization_id = {TENANT}",
    "workspaces": f"organization_id = {TENANT} OR id = ANY(app_linked_workspaces())",
    "websites": f"organization_id = {TENANT} OR workspace_id = ANY(app_linked_workspaces())",
    # An agency's member assignments, and assignments to this organization's workspaces
    # (so a business ending a grant can remove the agency's assignments).
    "workspace_assignments": (
        "organization_id = app_tenant() OR workspace_id IN "
        "(SELECT w.id FROM workspaces w WHERE w.organization_id = app_tenant())"),
    "workspace_grants": f"organization_id = {TENANT} OR agency_organization_id = {TENANT}",
}


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION app_tenant() RETURNS uuid LANGUAGE sql STABLE AS $$
            SELECT nullif(current_setting('app.org_id', true), '')::uuid
        $$
    """)
    op.execute("""
        CREATE FUNCTION app_linked_workspaces() RETURNS uuid[] LANGUAGE sql STABLE AS $$
            SELECT coalesce(string_to_array(nullif(current_setting('app.linked_ws', true), ''),
                                            ',')::uuid[], '{}')
        $$
    """)
    for table, condition in POLICIES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} "
                   f"USING ({UNSET} OR {condition}) WITH CHECK ({UNSET} OR {condition})")
    # The activity log: read only your own; writing is allowed (an agency's change in a
    # business's shared workspace is recorded in both organizations' logs).
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_read ON audit_logs FOR SELECT "
               f"USING ({UNSET} OR organization_id = {TENANT})")
    op.execute("CREATE POLICY tenant_write ON audit_logs FOR INSERT WITH CHECK (true)")


def downgrade() -> None:
    op.execute("DROP POLICY tenant_write ON audit_logs")
    op.execute("DROP POLICY tenant_read ON audit_logs")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")
    for table in reversed(list(POLICIES)):
        op.execute(f"DROP POLICY tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION app_linked_workspaces()")
    op.execute("DROP FUNCTION app_tenant()")
