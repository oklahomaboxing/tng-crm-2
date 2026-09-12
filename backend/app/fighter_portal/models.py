from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from ..database import Base


class FighterAccount(Base):
    __tablename__ = "fighter_accounts"

    id = Column(Integer, primary_key=True, index=True)

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    activated_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class FighterInvite(Base):
    __tablename__ = "fighter_invites"

    id = Column(Integer, primary_key=True, index=True)

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
        index=True,
    )

    token_hash = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    used_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )
