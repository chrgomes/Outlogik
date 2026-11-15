"""Imports every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""

from app.core.models import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import EmailVerificationToken, PasswordResetToken, UserSession
from app.modules.clients.models import Client, ClientUser
from app.modules.organizations.models import Invitation, Organization, OrganizationMember
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.site.models import ProductModule, SiteSettings
from app.modules.users.models import User
from app.modules.websites.models import Website

__all__ = [
    "AuditLog", "Base", "Client", "ClientUser", "EmailVerificationToken", "Invitation",
    "Organization", "OrganizationMember", "PasswordResetToken", "Permission", "ProductModule",
    "Role", "RolePermission", "SiteSettings", "User", "UserSession", "Website",
]
