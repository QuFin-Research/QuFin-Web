from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.auth import AppSettings, CurrentUser, Users
from app.core.config import Settings
from app.core.security import new_session_token
from app.schemas.auth import SignIn, SignUp, User
from app.stores.users import EmailTakenError, UserStore

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _check_rate_limit(request: Request, email: str) -> None:
    client = request.client.host if request.client else "unknown"
    limiter = request.app.state.auth_limiter
    # Separate budgets per IP and per account, so neither spraying one password across
    # accounts nor guessing one account's password from many IPs gets far.
    retry_after = limiter.hit(f"ip:{client}") or limiter.hit(f"email:{email}")
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )


def _start_session(response: Response, users: UserStore, user: User, settings: Settings) -> None:
    token = new_session_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    users.start_session(user.id, token, ttl)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )


@router.post("/sign-up", response_model=User, status_code=201)
def sign_up(
    data: SignUp, request: Request, response: Response, users: Users, settings: AppSettings
) -> User:
    """Create an account and sign in."""
    _check_rate_limit(request, data.email)
    try:
        user = users.create(data.email, data.password)
    except EmailTakenError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    _start_session(response, users, user, settings)
    return user


@router.post("/sign-in", response_model=User)
def sign_in(
    data: SignIn, request: Request, response: Response, users: Users, settings: AppSettings
) -> User:
    _check_rate_limit(request, data.email)
    user = users.authenticate(data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    # Any session the browser already had is replaced, never reused.
    if old := request.cookies.get(settings.session_cookie_name):
        users.end_session(old)
    _start_session(response, users, user, settings)
    return user


@router.post("/sign-out", status_code=204)
def sign_out(request: Request, users: Users, settings: AppSettings) -> Response:
    if token := request.cookies.get(settings.session_cookie_name):
        users.end_session(token)
    response = Response(status_code=204)
    response.delete_cookie(
        settings.session_cookie_name,
        domain=settings.cookie_domain,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=User)
def me(user: CurrentUser) -> User:
    return user
