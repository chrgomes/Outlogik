"""Imports every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""

from app.core.models import Base
from app.jobs.models import Job
from app.modules.audit.models import AuditLog
from app.modules.audits.models import Audit, AuditIssue, AuditPage, UsageRecord
from app.modules.auth.models import EmailVerificationToken, PasswordResetToken, UserSession
from app.modules.clients.models import Client, ClientUser
from app.modules.dashboard.models import WorkspaceReview
from app.modules.grants.models import WorkspaceGrant
from app.modules.integrations.models import (
    DataSource,
    Ga4Breakdown,
    Ga4Daily,
    Ga4Page,
    GscDaily,
    GscPage,
    GscQuery,
    GscQueryPage,
    Integration,
)
from app.modules.leads.models import Lead, LeadNote, NewsletterSubscriber
from app.modules.organizations.models import Invitation, Organization, OrganizationMember
from app.modules.plans.models import Plan, PlanEntitlement, Subscription
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.site.models import PortalFeature, SiteSettings
from app.modules.users.models import User
from app.modules.websites.models import Website
from app.modules.workspaces.models import Workspace, WorkspaceAssignment

__all__ = [
    "Audit",
    "AuditIssue",
    "AuditLog",
    "AuditPage",
    "Base",
    "Client",
    "ClientUser",
    "DataSource",
    "EmailVerificationToken",
    "Ga4Breakdown",
    "Ga4Page",
    "Ga4Daily",
    "GscDaily",
    "GscPage",
    "GscQuery",
    "GscQueryPage",
    "Integration",
    "Invitation",
    "Job",
    "Lead", "LeadNote",
    "NewsletterSubscriber",
    "Organization",
    "OrganizationMember",
    "PasswordResetToken",
    "Plan",
    "PlanEntitlement",
    "Permission",
    "PortalFeature",
    "Role",
    "RolePermission",
    "SiteSettings",
    "Subscription",
    "UsageRecord",
    "User",
    "UserSession",
    "Website",
    "Workspace",
    "WorkspaceGrant",
    "WorkspaceReview",
    "WorkspaceAssignment",
]
