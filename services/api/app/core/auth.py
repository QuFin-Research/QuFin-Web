"""Request dependencies for settings and the signed-in user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.auth import User
from app.stores.db import get_session
from app.stores.users import UserStore


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[Session, Depends(get_session)]


def get_user_store(session: DbSession) -> UserStore:
    return UserStore(session)


Users = Annotated[UserStore, Depends(get_user_store)]


def current_user(request: Request, settings: AppSettings, users: Users) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = users.user_for_token(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
