"""What a plan can limit, and the plans Outlogik starts with.

Entitlement keys are defined here (so nothing can be limited that the code doesn't check);
their values live in the database, so plans can change without a code change.
Approved plans and prices: docs/HYBRID_SAAS_PLAN.md §1.4.
"""

ENTITLEMENTS: dict[str, str] = {
    "limits.websites": "Websites (archived ones don't count)",
    "limits.clients": "Clients (archived ones don't count)",
    "limits.team_members": "Team members (client-portal users don't count)",
}

TRIAL_DAYS = 14
STATUSES = ("trialing", "active", "past_due", "cancelled")
INTERVALS = ("monthly", "annual")

# Seeded by migration 0013. Prices in Canadian cents; annual is 20% off, paid upfront.
# A limit of None means unlimited; 0 means not included.
DEFAULT_PLANS = [
    {"key": "digital_starter", "name": "Digital Starter", "account_kind": "business",
     "monthly": 2900, "annual": 27840, "limits": {"websites": 1, "clients": 0, "team_members": 2}},
    {"key": "digital_growth", "name": "Digital Growth", "account_kind": "business",
     "monthly": 5900, "annual": 56640, "limits": {"websites": 3, "clients": 0, "team_members": 5}},
    {"key": "digital_professional", "name": "Digital Professional", "account_kind": "business",
     "monthly": 9900, "annual": 95040,
     "limits": {"websites": 10, "clients": 0, "team_members": 10}},
    {"key": "agency_starter", "name": "Agency Starter", "account_kind": "agency",
     "monthly": 7900, "annual": 75840, "limits": {"websites": 10, "clients": 5, "team_members": 3}},
    {"key": "agency_professional", "name": "Agency Professional", "account_kind": "agency",
     "monthly": 14900, "annual": 143040,
     "limits": {"websites": 30, "clients": 15, "team_members": 8}},
    {"key": "agency_business", "name": "Agency Business", "account_kind": "agency",
     "monthly": 29900, "annual": 287040,
     "limits": {"websites": 100, "clients": 40, "team_members": 20}},
]

# A new sign-up's free trial: the full (top) plan for its account type, until sign-up lets
# people choose (H1-11).
TRIAL_PLAN = {"business": "digital_professional", "agency": "agency_business"}
