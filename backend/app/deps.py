from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.errors import Forbidden, Unauthorized
from app.models import User
from app.models.enums import Role
from app.security import decode_access_token

SessionDep = Annotated[Session, Depends(get_session)]


def _token_from_request(request: Request) -> str | None:
    token = request.cookies.get(settings.cookie_name)
    if token:
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def get_optional_user(request: Request, session: SessionDep) -> User | None:
    token = _token_from_request(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = session.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise Unauthorized("Please log in to continue.")
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    allowed = frozenset(roles)

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise Forbidden("Your account role does not have access to this action.")
        return user

    return checker


StaffUser = Annotated[User, Depends(require_roles(Role.REVIEWER, Role.ADMIN))]
ListerUser = Annotated[User, Depends(require_roles(Role.AGENT, Role.LANDLORD))]
RenterUser = Annotated[User, Depends(require_roles(Role.RENTER))]
AgentUser = Annotated[User, Depends(require_roles(Role.AGENT))]
