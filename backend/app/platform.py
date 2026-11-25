"""Outlogik staff access: the website admin and the platform (Super Admin) area.

Staff roles are separate from organization roles, one per person, granted with the CLI:
- content_editor: website content and media (milestone B)
- site_admin: the website admin (leads, newsletter, settings, module statuses)
- platform_admin: organizations, users, plans, suspensions and sign-up codes
- support_admin: sees organizations and users; suspends and reactivates users
- billing_admin: sees organizations and users; assigns plans and trials
Super Admins (a flag, CLI only) can do everything, and count as site admins.
"""

from collections.abc import Callable

from fastapi import Depends

from app.core.errors import NotFound
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User

CONTENT_EDITOR, SITE_ADMIN = "content_editor", "site_admin"
PLATFORM_ADMIN, SUPPORT_ADMIN, BILLING_ADMIN = "platform_admin", "support_admin", "billing_admin"

# Platform (Super Admin area) capabilities, by staff role
PLATFORM_CAPS: dict[str, frozenset[str]] = {
    PLATFORM_ADMIN: frozenset({"platform.read", "users.suspend", "orgs.suspend", "plans.assign",
                               "signup_codes.manage"}),
    SUPPORT_ADMIN: frozenset({"platform.read", "users.suspend"}),
    BILLING_ADMIN: frozenset({"platform.read", "plans.assign"}),
}
ALL_CAPS = frozenset().union(*PLATFORM_CAPS.values())


def platform_caps(user: User) -> frozenset[str]:
    if user.is_super_admin:
        return ALL_CAPS
    return PLATFORM_CAPS.get(user.platform_role or "", frozenset())


def require_platform(cap: str) -> Callable[..., User]:
    """Dependency: the signed-in staff member if they have `cap`. Everyone else gets 404, so the
    platform API doesn't reveal itself."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if cap not in platform_caps(user):
            raise NotFound()
        return user

    _dependency.platform_cap = cap  # type: ignore[attr-defined]  # checked by tests
    return _dependency


def staff_role(user: User) -> str | None:
    """The staff role for the website admin (Super Admins count as site admins)."""
    if user.is_super_admin:
        return SITE_ADMIN
    return user.platform_role


def require_staff(*roles: str) -> Callable[..., User]:
    """Dependency: the signed-in user if they hold one of `roles` (site admins pass every check).
    Everyone else gets 404, so the admin API doesn't reveal itself."""
    allowed = set(roles) | {SITE_ADMIN}

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if staff_role(user) not in allowed:
            raise NotFound()
        return user

    _dependency.staff_roles = allowed  # type: ignore[attr-defined]  # checked by tests
    return _dependency
