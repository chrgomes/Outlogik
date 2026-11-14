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
}

OWNER, ADMIN, MEMBER, CLIENT = "owner", "admin", "member", "client"

_ALL = set(PERMISSIONS)

DEFAULT_ROLES: dict[str, dict] = {
    OWNER: {
        "name": "Owner",
        "description": "Full control of the organization.",
        "permissions": _ALL,
    },
    ADMIN: {
        "name": "Admin",
        "description": "Manages the team, clients and websites. Cannot change owners.",
        "permissions": _ALL,
    },
    MEMBER: {
        "name": "Team Member",
        "description": "Works on clients and websites.",
        "permissions": {
            "organization.read", "members.read", "roles.read", "clients.read", "clients.write",
            "websites.read", "websites.write", "dashboard.read",
        },
    },
    CLIENT: {
        "name": "Client",
        "description": "Client-portal access, limited to the clients they are linked to.",
        "permissions": {"organization.read", "clients.read", "websites.read", "dashboard.read"},
    },
}
