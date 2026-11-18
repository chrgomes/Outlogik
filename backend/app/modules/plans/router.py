from fastapi import APIRouter, Depends

from app.core.errors import NotFound
from app.modules.auth.deps import DB
from app.modules.plans import service
from app.modules.plans.catalogue import ENTITLEMENTS
from app.modules.plans.models import Plan
from app.modules.plans.schemas import LimitOut, PlanOut, SubscriptionOut
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}", tags=["plans"])


@router.get("/subscription", response_model=SubscriptionOut,
            summary="This organization's plan, its limits and current usage")
def subscription(db: DB, ctx: OrgContext = Depends(require("plan.read"))):
    sub = service.subscription_for(db, ctx.org.id)
    if sub is None:
        raise NotFound("This organization has no plan.")
    plan = db.get(Plan, sub.plan_id)
    allowed, used = service.limits(db, plan.id), service.usage(db, ctx.org.id)
    shown = [k for k in ENTITLEMENTS if not (k == "limits.clients" and ctx.org.kind != "agency")]
    return SubscriptionOut(
        plan=PlanOut(key=plan.key, name=plan.name, account_kind=plan.account_kind,
                     currency=plan.currency, monthly_price_cents=plan.monthly_price_cents,
                     annual_price_cents=plan.annual_price_cents),
        status=service.effective_status(sub), billing_interval=sub.billing_interval,
        trial_ends_at=sub.trial_ends_at, current_period_end=sub.current_period_end,
        limits=[LimitOut(key=k, label=ENTITLEMENTS[k], limit=allowed[k], used=used[k])
                for k in shown])
