from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from app.database import Base

class KioskDevice(Base):
    __tablename__ = 'checkin_kiosk_devices'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    confirmation_seconds = Column(Integer, default=8, nullable=False)
    duplicate_seconds = Column(Integer, default=120, nullable=False)
    credential_hash = Column(String(64), unique=True, nullable=True)
    pairing_hash = Column(String(64), unique=True, nullable=True)
    pairing_expires = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class KioskAttempt(Base):
    __tablename__ = 'checkin_kiosk_attempts'
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('checkin_kiosk_devices.id'), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey('members.id', ondelete='SET NULL'), nullable=True)
    attendance_id = Column(Integer, ForeignKey('attendance.id', ondelete='SET NULL'), nullable=True)
    outcome = Column(String(24), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

class KioskRateBucket(Base):
    __tablename__ = 'checkin_kiosk_rate_buckets'
    key = Column(String(64), primary_key=True)
    window = Column(Integer, nullable=False)
    count = Column(Integer, default=0, nullable=False)
