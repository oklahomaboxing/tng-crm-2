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
    clover_customer_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    sales = relationship("Sale", back_populates="member")

class MembershipProduct(Base):
    __tablename__ = "membership_products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    recurring = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

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

class CloverSetting(Base):
    __tablename__ = "clover_settings"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(String, default="")
    environment = Column(String, default="sandbox")
    webhook_secret = Column(String, default="")
    access_token_note = Column(String, default="Store production token in environment variables, not database.")
