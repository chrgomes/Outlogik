from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PlanOut(BaseModel):
    key: str
    name: str
    account_kind: Literal["business", "agency"]
    currency: str
    monthly_price_cents: int
    annual_price_cents: int


class LimitOut(BaseModel):
    key: str
    label: str
    # None: unlimited
    limit: int | None
    # None for caps that aren't counted (pages per audit)
    used: int | None


class SubscriptionOut(BaseModel):
    plan: PlanOut
    status: Literal["trialing", "active", "past_due", "cancelled", "trial_ended"]
    billing_interval: Literal["monthly", "annual"]
    trial_ends_at: datetime | None
    current_period_end: datetime | None
    limits: list[LimitOut]
