"""Request dependencies for settings and the signed-in user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.auth import Role, User
from app.stores.db import get_session
from app.stores.users import UserStore


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[Session, Depends(get_session)]


def get_user_store(session: DbSession) -> UserStore:
    return UserStore(session)


Users = Annotated[UserStore, Depends(get_user_store)]


def role_of(email: str, settings: Settings) -> Role:
    """The role the server's settings give an email address."""
    address = email.strip().lower()
    if address in settings.admin_emails:
        return "admin"
    if address in settings.data_scientist_emails:
        return "data_scientist"
    return "user"


def with_role(user: User, settings: Settings) -> User:
    return user.model_copy(update={"role": role_of(user.email, settings)})


def current_user(request: Request, settings: AppSettings, users: Users) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = users.user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return with_role(user, settings)


CurrentUser = Annotated[User, Depends(current_user)]


def require_staff(user: CurrentUser) -> User:
    """Admins and data scientists: they may read the admin views."""
    if user.role not in ("admin", "data_scientist"):
        raise HTTPException(status_code=403, detail="Admins and data scientists only")
    return user


def require_admin(user: CurrentUser) -> User:
    """Admins only: they may also start jobs that call outside data sources."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user


Staff = Annotated[User, Depends(require_staff)]
Admin = Annotated[User, Depends(require_admin)]
