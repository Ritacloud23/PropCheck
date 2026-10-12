from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import select

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.errors import Conflict, Unauthorized
from app.models import User
from app.models.enums import Role
from app.schemas.auth import AuthOut, LoginIn, RegisterIn, UserOut
from app.security import create_access_token, hash_password, verify_password
from app.services import audit, ratelimit
from app.services.ratelimit import limit

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


@router.post(
    "/register", response_model=AuthOut, status_code=201, dependencies=[Depends(limit("register", by="ip"))]
)
async def register(body: RegisterIn, response: Response, session: SessionDep) -> AuthOut:
    """Create a renter, agent or landlord account. Reviewer/admin accounts are provisioned by an admin."""
    email = body.email.lower()
    if (await session.exec(select(User).where(User.email == email))).first():
        raise Conflict("An account with this email already exists.")
    user = User(
        full_name=body.full_name,
        email=email,
        phone=body.phone,
        password_hash=await hash_password(body.password),
        role=Role(body.role),
    )
    session.add(user)
    await session.flush()
    audit.record(
        session, actor_id=user.id, entity_type="User", entity_id=user.id, action="USER_REGISTERED",
        to_status=user.role.value,
    )  # fmt: skip
    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    _set_session_cookie(response, token)
    return AuthOut(user=UserOut.model_validate(user), access_token=token)


@router.post("/login", response_model=AuthOut)
async def login(body: LoginIn, request: Request, response: Response, session: SessionDep) -> AuthOut:
    # Counted before the password check: per IP + account (brute force on one account) and per IP
    # across accounts (password spraying). Shared networks (CGNAT) only share the looser IP limit.
    ip = ratelimit.client_ip(request)
    await ratelimit.enforce("login_ip", f"ip:{ip}")
    await ratelimit.enforce("login", f"ip:{ip}:account:{ratelimit.account_key(body.email)}")
    user = (await session.exec(select(User).where(User.email == body.email.lower()))).first()
    # Same message for unknown email and wrong password (no account enumeration).
    if not user or not await verify_password(body.password, user.password_hash):
        raise Unauthorized("Incorrect email or password.")
    if not user.is_active:
        raise Unauthorized("This account has been deactivated.")
    token = create_access_token(user.id, user.role.value)  # type: ignore[arg-type]
    _set_session_cookie(response, token)
    return AuthOut(user=UserOut.model_validate(user), access_token=token)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    response.delete_cookie(settings.cookie_name, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
