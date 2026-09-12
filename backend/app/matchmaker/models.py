from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, LargeBinary
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

    instagram = Column(String, default="")
    facebook = Column(String, default="")
    tiktok = Column(String, default="")
    twitter = Column(String, default="")

    submitted_by_name = Column(String, default="")
    submitted_by_role = Column(String, default="")
    submitted_by_phone = Column(String, default="")
    submitted_by_email = Column(String, default="")

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
    bloodwork_provider = Column(String, default="")
    bloodwork_requested_date = Column(String, default="")
    bloodwork_completed_date = Column(String, default="")
    bloodwork_notes = Column(Text, default="")

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
    bout_order = Column(Integer, default=0)
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


class BoxingEventChecklist(Base):
    __tablename__ = "boxing_event_checklist"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("boxing_events.id"),
        nullable=False,
        index=True,
    )

    section = Column(String, nullable=False)
    item_key = Column(String, nullable=False)
    label = Column(Text, nullable=False)

    status = Column(String, default="not_started")
    due_date = Column(String, default="")
    assigned_to = Column(String, default="")
    notes = Column(Text, default="")

    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BoxingEventFee(Base):
    __tablename__ = "boxing_event_fees"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(
        Integer,
        ForeignKey("boxing_events.id"),
        nullable=False,
        index=True,
    )

    fee_key = Column(String, nullable=False)
    name = Column(String, nullable=False)
    estimate = Column(String, default="")

    actual_amount = Column(Float, nullable=True)
    paid = Column(Boolean, default=False)

    due_date = Column(String, default="")
    payee = Column(String, default="")
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BoxingContract(Base):
    __tablename__ = "boxing_contracts"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(
        Integer,
        ForeignKey("boxing_events.id"),
        nullable=False,
        index=True,
    )

    bout_id = Column(
        Integer,
        ForeignKey("boxing_bouts.id"),
        nullable=False,
        index=True,
    )

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
        index=True,
    )

    opponent_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
    )

    corner = Column(String, nullable=False)

    contract_date = Column(String, default="")

    boxer_name = Column(String, default="")
    boxer_federal_id = Column(String, default="")
    boxer_address = Column(String, default="")
    boxer_phone = Column(String, default="")
    boxer_manager = Column(String, default="")

    opponent_name = Column(String, default="")

    rounds = Column(Integer, default=4)
    maximum_weight = Column(Float, nullable=True)

    event_name = Column(String, default="")
    event_date = Column(String, default="")
    venue = Column(String, default="")
    venue_address = Column(String, default="")

    promoter_name = Column(String, default="")
    promoter_address = Column(String, default="")
    promoter_phone = Column(String, default="")
    promoter_matchmaker = Column(String, default="")

    gross_purse = Column(Float, default=0)

    # Travel / lodging package
    travel_type = Column(String, default="")
    travel_paid_by = Column(String, default="")
    travel_expense = Column(Float, default=0)

    hotel_provided = Column(String, default="")
    hotel_name = Column(String, default="")
    hotel_nights = Column(Integer, default=0)

    per_diem_daily = Column(Float, default=0)
    per_diem_days = Column(Integer, default=0)
    per_diem_total = Column(Float, default=0)

    deductions = Column(Float, default=0)
    boxer_paid = Column(Float, default=0)

    additional_terms = Column(Text, default="")
    cancellation_pay = Column(Float, default=0)

    status = Column(String, default="draft")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BoxingSignedContractDocument(Base):
    __tablename__ = "boxing_signed_contract_documents"

    id = Column(Integer, primary_key=True, index=True)

    # One current signed document per contract.
    contract_id = Column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    file_name = Column(String, default="")
    content_type = Column(
        String,
        default="application/pdf",
    )
    file_size = Column(Integer, default=0)

    # Stored privately in Postgres.
    # This is never exposed through /uploads.
    file_data = Column(
        LargeBinary,
        nullable=False,
    )

    source = Column(
        String,
        default="staff_upload",
    )

    uploaded_by_user_id = Column(
        Integer,
        nullable=True,
    )
    uploaded_by_name = Column(
        String,
        default="",
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BoxingSeries(Base):
    __tablename__ = "boxing_series"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)

    description = Column(Text, default="")
    target_fights = Column(Integer, default=5)
    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BoxingSeriesFighter(Base):
    __tablename__ = "boxing_series_fighters"

    id = Column(Integer, primary_key=True, index=True)

    series_id = Column(
        Integer,
        ForeignKey("boxing_series.id"),
        nullable=False,
        index=True,
    )

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
        index=True,
    )

    signed_date = Column(String, default="")
    start_record = Column(String, default="")

    target_fights = Column(Integer, default=5)
    fights_completed = Column(Integer, default=0)

    status = Column(String, default="active")
    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    series = relationship("BoxingSeries")
    fighter = relationship("BoxingFighter")


class BoxingSignedFighter(Base):
    __tablename__ = "boxing_signed_fighters"

    id = Column(Integer, primary_key=True, index=True)

    fighter_id = Column(
        Integer,
        ForeignKey("boxing_fighters.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    signed_date = Column(String, default="")
    start_date = Column(String, default="")
    end_date = Column(String, default="")

    agreement_type = Column(String, default="development")
    status = Column(String, default="active")

    exclusive = Column(Boolean, default=False)
    contract_on_file = Column(Boolean, default=False)

    notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    fighter = relationship("BoxingFighter")


class BoxingEventPublication(Base):
    __tablename__ = "boxing_event_publications"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(
        Integer,
        ForeignKey("boxing_events.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    published = Column(Boolean, default=False)

    public_title = Column(String, default="")
    doors_time = Column(String, default="")
    first_bout_time = Column(String, default="")

    ticket_url = Column(String, default="")
    poster_url = Column(String, default="")

    public_notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    event = relationship("BoxingEvent")

class BoxingContractSignature(Base):
    __tablename__ = "boxing_contract_signatures"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    contract_id = Column(
        Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    fighter_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    signer_user_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    typed_legal_name = Column(
        String,
        nullable=False,
        default="",
    )

    agreed = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    signed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    template_version = Column(
        String,
        nullable=False,
        default="oklahoma-boxing-contract-v1",
    )

    # Exact authoritative contract terms at signing.
    contract_snapshot = Column(
        Text,
        nullable=False,
    )

    snapshot_sha256 = Column(
        String(64),
        nullable=False,
        index=True,
    )

    signer_ip = Column(
        String,
        default="",
    )

    signer_user_agent = Column(
        Text,
        default="",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

