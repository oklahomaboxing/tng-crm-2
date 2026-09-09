from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Text
from sqlalchemy.orm import relationship
from ..database import Base


class MemberAccount(Base):
    __tablename__ = "member_accounts"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    activated_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    inbody_user_id = Column(String, nullable=True, index=True)
    inbody_linked_at = Column(DateTime, nullable=True)
    inbody_last_synced_at = Column(DateTime, nullable=True)
    member_consent_inbody = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MemberInvite(Base):
    __tablename__ = "member_invites"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InBodyScan(Base):
    __tablename__ = "inbody_scans"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    inbody_test_id = Column(String, unique=True, nullable=True, index=True)
    scan_date = Column(DateTime, nullable=False, index=True)

    weight = Column(Float, nullable=True)
    skeletal_muscle_mass = Column(Float, nullable=True)
    body_fat_mass = Column(Float, nullable=True)
    percent_body_fat = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    visceral_fat_level = Column(Float, nullable=True)
    bmr = Column(Float, nullable=True)
    inbody_score = Column(Float, nullable=True)

    raw_data = Column(Text, nullable=True)
    source = Column(String, default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)

