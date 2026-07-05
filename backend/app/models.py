from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="rep")  # admin, manager, rep
    active = Column(Boolean, default=True)
    rep_profile = relationship("SalesRep", back_populates="user", uselist=False)

class SalesRep(Base):
    __tablename__ = "sales_reps"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone = Column(String, default="")
    referral_slug = Column(String, unique=True, index=True, nullable=False)
    clover_link = Column(String, default="")
    user = relationship("User", back_populates="rep_profile")
    sales = relationship("Sale", back_populates="sales_rep")

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, default="")
    phone = Column(String, default="")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    sales = relationship("Sale", back_populates="member")
    member_number = Column(String, nullable=True)
    digital_member_id = Column(String, unique=True, nullable=True)
    barcode = Column(String, nullable=True)
    qr_code = Column(String, nullable=True)
    membership_start = Column(DateTime, nullable=True)
    membership_end = Column(DateTime, nullable=True)
    membership_status = Column(String, default="active")
    clover_customer_id = Column(String, nullable=True)
    auto_renew = Column(Boolean, default=False)
    assigned_coach = Column(String, nullable=True)
    waiver_signed = Column(Boolean, default=False)
    photo_url = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    membership_type = Column(String, nullable=True)
    membership_level = Column(String, default="Bronze")
    last_checkin = Column(DateTime, nullable=True)
    checkins = Column(Integer, default=0)
    total_checkins = Column(Integer, default=0)
    expires_soon = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    billing_cycle = Column(String, nullable=True)
    monthly_rate = Column(Float, default=0)
    next_billing_date = Column(DateTime, nullable=True)
    autopay_enabled = Column(Boolean, default=False)
    billing_status = Column(String, nullable=True)
    clover_subscription_id = Column(String, nullable=True)
    last_payment_date = Column(DateTime, nullable=True)
    past_due_amount = Column(Float, default=0)

class MembershipProduct(Base):
    __tablename__ = "membership_products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    recurring = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    category = Column(String, nullable=True)
    category = Column(String, nullable=True)
    is_membership = Column(Boolean, default=False)
    renews_monthly = Column(Boolean, default=False)
    autopay_allowed = Column(Boolean, default=False)
    default_membership_months = Column(Integer, default=1)


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    sales_rep_id = Column(Integer, ForeignKey("sales_reps.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("membership_products.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(String, default="pending")
    clover_order_id = Column(String, default="")
    clover_payment_id = Column(String, default="")
    sale_date = Column(DateTime, default=datetime.utcnow)
    member = relationship("Member", back_populates="sales")
    sales_rep = relationship("SalesRep", back_populates="sales")
    product = relationship("MembershipProduct")
    clover_checkout_id = Column(String, nullable=True)
    transaction_status = Column(String, default="paid")
    refunded = Column(Boolean, default=False)
    refund_amount = Column(Float, default=0)
    payment_method = Column(String, nullable=True)

class CloverSetting(Base):
    __tablename__ = "clover_settings"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String, default="")
    environment = Column(String, default="sandbox")
    webhook_secret = Column(String, default="")
    access_token_note = Column(String, default="Store production token in environment variables, not database.")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey("membership_products.id"), nullable=True)
    sales_rep_id = Column(Integer, ForeignKey("sales_reps.id"), nullable=True)
    referral_slug = Column(String, nullable=True)
    status = Column(String, default="new")
    clover_order_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    clover_checkout_id = Column(String, nullable=True)
    clover_payment_id = Column(String, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    converted_at = Column(DateTime, nullable=True)
    conversion_source = Column(String, default="qr_referral")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)

    checkin_time = Column(DateTime, default=datetime.utcnow)
    checkout_time = Column(DateTime, nullable=True)

    method = Column(String, default="barcode")
    location = Column(String, default="Front Desk")

    member = relationship("Member")
