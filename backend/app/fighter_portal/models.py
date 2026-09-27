from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, LargeBinary

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



class FighterPhoto(Base):
    __tablename__ = "fighter_photos"

    id = Column(Integer, primary_key=True, index=True)

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
        index=True,
    )

    file_name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_data = Column(LargeBinary, nullable=False)

    photo_type = Column(
        String,
        default="headshot",
        nullable=False,
    )

    is_primary = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class FighterPortalVideo(Base):
    __tablename__ = "fighter_portal_videos"

    id = Column(Integer, primary_key=True, index=True)

    youtube_video_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    youtube_url = Column(
        String,
        nullable=False,
    )

    title = Column(
        String,
        nullable=False,
    )

    thumbnail_url = Column(
        String,
        nullable=True,
    )

    category = Column(
        String,
        default="fight",
        nullable=False,
    )

    event_name = Column(
        String,
        nullable=True,
    )

    fighter_names = Column(
        String,
        nullable=True,
    )

    approved = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    sort_order = Column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
    )
