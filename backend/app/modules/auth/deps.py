from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import Unauthorized
from app.modules.auth.models import UserSession
from app.modules.auth.service import resolve_session
from app.modules.users.models import User


@dataclass
class AuthContext:
    session: UserSession
    user: User


def get_auth(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise Unauthorized()
    resolved = resolve_session(db, token)
    if resolved is None:
        raise Unauthorized("Your session has expired. Please sign in again.",
                           code="session_expired")
    return AuthContext(*resolved)


def get_optional_auth(request: Request, db: Session = Depends(get_db)) -> AuthContext | None:
    token = request.cookies.get(get_settings().session_cookie_name)
    resolved = resolve_session(db, token) if token else None
    return AuthContext(*resolved) if resolved else None


def get_current_user(auth: AuthContext = Depends(get_auth)) -> User:
    return auth.user


CurrentAuth = Annotated[AuthContext, Depends(get_auth)]
OptionalAuth = Annotated[AuthContext | None, Depends(get_optional_auth)]
CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]
