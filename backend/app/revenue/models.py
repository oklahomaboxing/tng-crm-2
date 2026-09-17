from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
)

from sqlalchemy.orm import relationship

from ..database import Base


class RevenueOrganization(Base):
    __tablename__ = "revenue_organizations"

    id = Column(Integer, primary_key=True, index=True)

    business_name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    industry = Column(String, nullable=True)
    employee_size = Column(String, nullable=True)

    facebook_url = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    # Estimated marketing behavior.
    # HIGH / MEDIUM / LOW / UNKNOWN
    marketing_propensity = Column(String, default="UNKNOWN")

    # True only when actual prior sponsorship evidence has been found.
    verified_sponsorship_history = Column(Boolean, nullable=True)

    # JSON stored as text for SQLite compatibility.
    marketing_evidence_json = Column(Text, default="[]")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    contacts = relationship(
        "RevenueOrganizationContact",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    prospects = relationship(
        "EventRevenueProspect",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class RevenueOrganizationContact(Base):
    __tablename__ = "revenue_organization_contacts"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("revenue_organizations.id"),
        nullable=False,
        index=True,
    )

    first_name = Column(String, default="")
    last_name = Column(String, default="")
    job_title = Column(String, nullable=True)

    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    primary_contact = Column(Boolean, default=False)

    # manual / website / public_directory / prior_relationship / other
    source = Column(String, default="manual")

    verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship(
        "RevenueOrganization",
        back_populates="contacts",
    )


class EventRevenuePackage(Base):
    __tablename__ = "event_revenue_packages"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    # SPONSOR / VENDOR / PARTNER
    package_type = Column(String, nullable=False, index=True)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    price = Column(Float, default=0)

    quantity_available = Column(Integer, nullable=True)
    quantity_sold = Column(Integer, default=0)

    # Clover hosted payment URL
    clover_payment_url = Column(String, nullable=True)

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EventRevenueProspect(Base):
    __tablename__ = "event_revenue_prospects"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("revenue_organizations.id"),
        nullable=False,
        index=True,
    )

    # SPONSOR / VENDOR / PARTNER
    prospect_type = Column(String, nullable=False, index=True)

    # Sponsor examples:
    # NEW / RESEARCHED / CONTACTED / REPLIED / INTERESTED /
    # PROPOSAL_SENT / NEGOTIATING / COMMITTED / PAID /
    # DECLINED / NO_RESPONSE
    #
    # Vendor examples:
    # NEW / INVITED / APPLICATION_SUBMITTED / APPROVED /
    # PAYMENT_PENDING / PAID / BOOTH_ASSIGNED / CHECKED_IN
    status = Column(String, default="NEW", index=True)

    fit_score = Column(Integer, default=0)

    marketing_activity_score = Column(Integer, default=0)
    sponsorship_history_score = Column(Integer, default=0)
    audience_fit_score = Column(Integer, default=0)
    business_capacity_score = Column(Integer, default=0)
    distance_score = Column(Integer, default=0)
    relationship_score = Column(Integer, default=0)

    recommended_package_id = Column(
        Integer,
        ForeignKey("event_revenue_packages.id"),
        nullable=True,
    )

    recommended_ask = Column(Float, nullable=True)

    # MANUAL / SPONSOR_SCOUT / VENDOR_SCOUT / IMPORT / PREVIOUS_EVENT
    lead_source = Column(String, default="MANUAL")

    distance_miles = Column(Float, nullable=True)

    assigned_to_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    last_contacted_at = Column(DateTime, nullable=True)
    next_follow_up_at = Column(DateTime, nullable=True)

    do_not_contact = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship(
        "RevenueOrganization",
        back_populates="prospects",
    )

    package = relationship(
        "EventRevenuePackage",
        foreign_keys=[recommended_package_id],
    )


class EventRevenueProposal(Base):
    __tablename__ = "event_revenue_proposals"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    prospect_id = Column(
        Integer,
        ForeignKey("event_revenue_prospects.id"),
        nullable=False,
        index=True,
    )

    package_id = Column(
        Integer,
        ForeignKey("event_revenue_packages.id"),
        nullable=True,
    )

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    proposal_url = Column(String, nullable=True)

    # Snapshot the Clover URL used when proposal was created.
    clover_payment_url = Column(String, nullable=True)

    # DRAFT / SENT / VIEWED / ACCEPTED / DECLINED / PAID
    status = Column(String, default="DRAFT", index=True)

    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class EventRevenuePayment(Base):
    __tablename__ = "event_revenue_payments"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    organization_id = Column(
        Integer,
        ForeignKey("revenue_organizations.id"),
        nullable=False,
        index=True,
    )

    prospect_id = Column(
        Integer,
        ForeignKey("event_revenue_prospects.id"),
        nullable=True,
        index=True,
    )

    package_id = Column(
        Integer,
        ForeignKey("event_revenue_packages.id"),
        nullable=True,
    )

    provider = Column(String, default="CLOVER")

    provider_payment_id = Column(String, nullable=True)

    payment_link = Column(String, nullable=True)

    amount = Column(Float, nullable=False)

    # PENDING / PAID / PARTIAL / FAILED / REFUNDED
    status = Column(String, default="PENDING", index=True)

    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class RevenueOutreachMessage(Base):
    __tablename__ = "revenue_outreach_messages"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    prospect_id = Column(
        Integer,
        ForeignKey("event_revenue_prospects.id"),
        nullable=False,
        index=True,
    )

    channel = Column(String, default="EMAIL")

    template_key = Column(String, nullable=True)

    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)

    # DRAFT / QUEUED / SENT / OPENED / CLICKED / REPLIED /
    # BOUNCED / FAILED / CANCELLED
    status = Column(String, default="DRAFT", index=True)

    provider_message_id = Column(String, nullable=True)

    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class EventVendorOperations(Base):
    __tablename__ = "event_vendor_operations"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(Integer, nullable=False, index=True)

    prospect_id = Column(
        Integer,
        ForeignKey("event_revenue_prospects.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    booth_number = Column(String, nullable=True)
    booth_size = Column(String, nullable=True)

    power_required = Column(Boolean, default=False)
    power_amps = Column(String, nullable=True)

    tables_required = Column(Integer, default=0)
    chairs_required = Column(Integer, default=0)

    food_vendor = Column(Boolean, default=False)

    food_permit_required = Column(Boolean, default=False)
    food_permit_received = Column(Boolean, default=False)

    insurance_required = Column(Boolean, default=False)
    insurance_received = Column(Boolean, default=False)

    arrival_time = Column(String, nullable=True)
    setup_time = Column(String, nullable=True)

    check_in_status = Column(String, default="NOT_CHECKED_IN")

    special_requests = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
