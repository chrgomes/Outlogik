import logging
import uuid
from collections.abc import Iterable, Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

log = logging.getLogger(__name__)

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

TENANT_KEY = "tenant"
_APPLY = text("SELECT set_config('app.org_id', :org, true), "
              "set_config('app.linked_ws', :linked, true)")


def _apply_tenant(connection, tenant: tuple[str, str]) -> None:
    org, linked = tenant
    connection.execute(_APPLY, {"org": org, "linked": linked})


def set_tenant(db: Session, org_id: uuid.UUID, linked: Iterable[uuid.UUID] = ()) -> None:
    """Limit this session to one organization at the database level (row-level security,
    migration 0012), for the rest of the request. Applied to the current transaction now,
    and to every later one: a request commits and starts new transactions as it goes, and
    the settings are transaction-local, so they never leak to the next user of the
    connection."""
    tenant = (str(org_id), ",".join(str(i) for i in linked))
    db.info[TENANT_KEY] = tenant
    if db.in_transaction():
        _apply_tenant(db.connection(), tenant)


@event.listens_for(Session, "after_begin")
def _tenant_on_begin(session: Session, transaction, connection) -> None:
    tenant = session.info.get(TENANT_KEY)
    if tenant:
        _apply_tenant(connection, tenant)


def check_row_level_security() -> None:
    """Superusers and BYPASSRLS roles ignore row-level security. Say so loudly."""
    try:
        with engine.connect() as conn:
            exempt = conn.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )).scalar()
    except Exception:  # the database may not be up yet; the health check reports that
        return
    if exempt:
        log.warning("The database user is a superuser or has BYPASSRLS, so row-level "
                    "security is NOT enforced. Use an ordinary user in production "
                    "(docs/DEPLOYMENT.md).")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
