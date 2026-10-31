"""User accounts and server-side sign-in sessions."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.security import hash_password, hash_token, needs_rehash, verify_password
from app.schemas.auth import User
from app.stores.db import Base, as_utc


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_schema(self) -> User:
        return User(id=self.id, email=self.email, created_at=as_utc(self.created_at))


class SessionRow(Base):
    __tablename__ = "sessions"

    # SHA-256 of the cookie token; the token itself is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class EmailTakenError(Exception):
    pass


class UserStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, email: str, password: str) -> User:
        row = UserRow(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise EmailTakenError from exc
        return row.to_schema()

    def authenticate(self, email: str, password: str) -> User | None:
        row = self.session.scalar(select(UserRow).where(UserRow.email == email))
        if not verify_password(row.password_hash if row else None, password) or row is None:
            return None
        if needs_rehash(row.password_hash):
            row.password_hash = hash_password(password)
            self.session.commit()
        return row.to_schema()

    def start_session(self, user_id: str, token: str, ttl: timedelta) -> None:
        now = datetime.now(UTC)
        # Opportunistic clean-up of expired sessions.
        self.session.execute(delete(SessionRow).where(SessionRow.expires_at < now))
        self.session.add(
            SessionRow(
                token_hash=hash_token(token), user_id=user_id, created_at=now, expires_at=now + ttl
            )
        )
        self.session.commit()

    def user_for_token(self, token: str) -> User | None:
        found = self.session.execute(
            select(UserRow, SessionRow.expires_at)
            .join(SessionRow, SessionRow.user_id == UserRow.id)
            .where(SessionRow.token_hash == hash_token(token))
        ).first()
        if found is None or as_utc(found.expires_at) <= datetime.now(UTC):
            return None
        return found.UserRow.to_schema()

    def end_session(self, token: str) -> None:
        self.session.execute(delete(SessionRow).where(SessionRow.token_hash == hash_token(token)))
        self.session.commit()
