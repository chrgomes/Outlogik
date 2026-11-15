"""Outlogik staff access (the admin area for the marketing website).

Staff roles are separate from organization roles:
- content_editor: website content and media (milestone B)
- site_admin: everything in the admin area, including leads, settings, pricing and module statuses
Super Admins count as site admins.
"""

from collections.abc import Callable

from fastapi import Depends

from app.core.errors import NotFound
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User

CONTENT_EDITOR, SITE_ADMIN = "content_editor", "site_admin"


def staff_role(user: User) -> str | None:
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
