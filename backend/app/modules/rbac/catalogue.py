"""The permission catalogue and the default roles created with every organization.

Permission codes are the contract between endpoints and roles: every endpoint declares
the code it needs, and roles are sets of codes.
"""

PERMISSIONS: dict[str, str] = {
    "organization.read": "View the organization",
    "organization.update": "Change organization settings",
    "members.read": "View team members",
    "members.invite": "Invite team members and client users",
    "members.update": "Change a member's role or status",
    "members.remove": "Remove members from the organization",
    "roles.read": "View roles and permissions",
    "roles.manage": "Create, edit and delete custom roles",
    "clients.read": "View clients",
    "clients.write": "Create and edit clients",
    "clients.delete": "Delete clients",
    "client_users.manage": "Grant and revoke client-portal access",
    "websites.read": "View websites",
    "websites.write": "Create and edit websites",
    "websites.delete": "Delete websites",
    "dashboard.read": "View the dashboard",
    "audit.read": "View the audit log",
    "access_grants.manage": "Give agencies access to your workspace, and revoke it",
    "linked_accounts.manage": "Accept and disconnect businesses' access to their workspaces",
}

OWNER, ADMIN, MEMBER, CLIENT = "owner", "admin", "member", "client"
VIEWER, ACCOUNT_MANAGER = "viewer", "account_manager"
BUSINESS, AGENCY = "business", "agency"
# A role sees every workspace in the organization, or only the ones its members are assigned to.
ALL_WORKSPACES, ASSIGNED_WORKSPACES = "all", "assigned"

_ALL = set(PERMISSIONS)

GROUP_LABELS = {
    "organization": "Organization", "members": "Team", "roles": "Roles",
    "clients": "Clients", "client_users": "Clients", "websites": "Websites",
    "dashboard": "Dashboard", "audit": "Audit log",
    "access_grants": "Agency access", "linked_accounts": "Linked businesses",
}


def permission_group(code: str) -> str:
    return GROUP_LABELS.get(code.split(".", 1)[0], "Other")

# Built-in roles. `kinds` says which account types get the role. Specialist roles (SEO
# Specialist, Content Creator, …) are added with the modules whose permissions set them apart.
DEFAULT_ROLES: dict[str, dict] = {
    OWNER: {
        "name": "Owner",
        "description": "Full control of the organization.",
        "permissions": _ALL,
        "kinds": {BUSINESS, AGENCY},
        "scope": ALL_WORKSPACES,
    },
    ADMIN: {
        "name": "Administrator",
        "description": "Manages the team, settings and all marketing work. Cannot change owners "
                       "or roles.",
        "permissions": _ALL - {"roles.manage"},
        "kinds": {BUSINESS, AGENCY},
        "scope": ALL_WORKSPACES,
    },
    MEMBER: {
        "name": "Marketing Manager",
        "description": "Works on websites and marketing in every workspace. Cannot manage the "
                       "team or settings.",
        "permissions": {
            "organization.read", "members.read", "roles.read", "clients.read", "clients.write",
            "websites.read", "websites.write", "dashboard.read",
        },
        "kinds": {BUSINESS, AGENCY},
        "scope": ALL_WORKSPACES,
    },
    ACCOUNT_MANAGER: {
        "name": "Account Manager",
        "description": "Manages the clients they're assigned to: their websites and "
                       "client-portal access.",
        "permissions": {
            "organization.read", "members.read", "roles.read", "clients.read",
            "client_users.manage", "websites.read", "websites.write", "dashboard.read",
        },
        "kinds": {AGENCY},
        "scope": ASSIGNED_WORKSPACES,
    },
    VIEWER: {
        "name": "Reporting Viewer",
        "description": "Read-only access to every workspace's websites and results.",
        "permissions": {"organization.read", "clients.read", "websites.read", "dashboard.read"},
        "kinds": {BUSINESS, AGENCY},
        "scope": ALL_WORKSPACES,
    },
    CLIENT: {
        "name": "Client Viewer",
        "description": "Client-portal access: read-only, limited to the clients they're "
                       "linked to.",
        "permissions": {"organization.read", "clients.read", "websites.read", "dashboard.read"},
        "kinds": {AGENCY},
        "scope": ASSIGNED_WORKSPACES,
    },
}


def roles_for(kind: str) -> dict[str, dict]:
    return {k: v for k, v in DEFAULT_ROLES.items() if kind in v["kinds"]}
