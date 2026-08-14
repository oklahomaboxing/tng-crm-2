from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base

class BoxingFighter(Base):
    __tablename__ = "boxing_fighters"

    id = Column(Integer, primary_key=True, index=True)
    legal_name = Column(String, nullable=False, index=True)
    dob = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    nationality = Column(String, default="")
    address = Column(String, default="")
    city = Column(String, default="")
    state = Column(String, default="")
    country = Column(String, default="")
    stance = Column(String, default="")
    gym = Column(String, default="")
    coach = Column(String, default="")
    height_in = Column(Integer, nullable=True)
    reach_in = Column(Integer, nullable=True)
    walk_weight = Column(Float, nullable=True)
    fight_weight = Column(Float, nullable=True)
    pro_record = Column(String, default="")
    amateur_record = Column(String, default="")
    boxrec_url = Column(String, default="")
    boxrec_id = Column(String, default="")

    manager_name = Column(String, default="")
    manager_phone = Column(String, default="")
    manager_email = Column(String, default="")

    ok_license_status = Column(String, default="unknown")
    ok_license_number = Column(String, default="")
    federal_id_status = Column(String, default="unknown")
    federal_id_number = Column(String, default="")
    suspension_status = Column(String, default="needs_review")
    suspension_notes = Column(Text, default="")
    bloodwork_status = Column(String, default="missing")
    bloodwork_expires = Column(String, default="")

    available = Column(Boolean, default=True)
    available_weight_min = Column(Float, nullable=True)
    available_weight_max = Column(Float, nullable=True)
    last_fight_date = Column(String, default="")

    source = Column(String, default="tng_os")
    source_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BoxingEvent(Base):
    __tablename__ = "boxing_events"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    venue = Column(String, default="")
    venue_address = Column(String, default="")
    event_date = Column(String, default="")
    status = Column(String, default="planning")
    created_at = Column(DateTime, default=datetime.utcnow)

class BoxingBout(Base):
    __tablename__ = "boxing_bouts"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id"), nullable=True, index=True)
    red_fighter_id = Column(Integer, ForeignKey("boxing_fighters.id"), nullable=False)
    blue_fighter_id = Column(Integer, ForeignKey("boxing_fighters.id"), nullable=False)
    weight_agreed = Column(Float, nullable=True)
    rounds = Column(Integer, default=4)
    bout_type = Column(String, default="pro")
    status = Column(String, default="draft")
    red_purse = Column(Float, default=0)
    blue_purse = Column(Float, default=0)
    match_score = Column(Integer, nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("BoxingEvent")
    red_fighter = relationship("BoxingFighter", foreign_keys=[red_fighter_id])
    blue_fighter = relationship("BoxingFighter", foreign_keys=[blue_fighter_id])
