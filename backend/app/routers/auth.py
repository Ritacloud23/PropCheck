from fastapi import APIRouter, Depends, Response
from sqlmodel import select

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.errors import Conflict, Unauthorized
from app.models import User
from app.models.enums import Role
from app.schemas.auth import AuthOut, LoginIn, RegisterIn, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.services import audit
from app.services.ratelimit import auth_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.cookie_name,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=AuthOut, status_code=201, dependencies=[Depends(auth_rate_limit)])
def register(body: RegisterIn, response: Response, session: SessionDep) -> AuthOut:
    """Create a renter, agent or landlord account. Reviewer/admin accounts are provisioned by an admin."""
    email = body.email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise Conflict("An account with this email already exists.")
    user = User(
        full_name=body.full_name,
        email=email,
        phone=body.phone,
        password_hash=hash_password(body.password),
        role=Role(body.role),
    )
    session.add(user)
    session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="User", entity_id=user.id, action="USER_REGISTERED",
        to_status=user.role.value,
    )  # fmt: skip
    session.commit()
    session.refresh(user)
    token = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    _set_session_cookie(response, token)
    return AuthOut(user=UserOut.model_validate(user), access_token=token)


@router.post("/login", response_model=AuthOut, dependencies=[Depends(auth_rate_limit)])
def login(body: LoginIn, response: Response, session: SessionDep) -> AuthOut:
    user = session.exec(select(User).where(User.email == body.email.lower())).first()
    # Same message for unknown email and wrong password (no account enumeration).
    if not user or not verify_password(body.password, user.password_hash):
        raise Unauthorized("Incorrect email or password.")
    if not user.is_active:
        raise Unauthorized("This account has been deactivated.")
    token = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    _set_session_cookie(response, token)
    return AuthOut(user=UserOut.model_validate(user), access_token=token)


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(settings.cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
