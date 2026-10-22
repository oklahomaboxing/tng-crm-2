from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class EventTicketType(Base):
    __tablename__ = "event_ticket_types"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(80), nullable=False)
    price_cents = Column(Integer, nullable=False)
    inventory = Column(Integer, nullable=True)
    commission_type = Column(String(20), default="percent")  # percent|flat|none
    commission_value = Column(Numeric(10,2), default=20)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class EventSeller(Base):
    __tablename__ = "event_sellers"
    __table_args__ = (UniqueConstraint("event_id", "seller_type", "seller_ref_id", name="uq_event_seller_ref"),)
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    seller_type = Column(String(20), nullable=False)  # fighter|sales_rep|staff|affiliate
    seller_ref_id = Column(Integer, nullable=False)   # fighter/user/rep id
    display_name = Column(String(160), nullable=False)
    email = Column(String(255), nullable=True)
    public_code = Column(String(40), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TicketSmsConsent(Base):
    __tablename__ = "ticket_sms_consents"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("ticket_orders.id"), unique=True, nullable=False)
    phone = Column(String(40), nullable=False)
    notice_version = Column(String(40), nullable=False)
    notice_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class TicketOrder(Base):
    __tablename__ = "ticket_orders"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    seller_id = Column(Integer, ForeignKey("event_sellers.id"), index=True, nullable=True)
    buyer_name = Column(String(160), nullable=False)
    buyer_email = Column(String(255), nullable=False, index=True)
    buyer_phone = Column(String(40), nullable=True)
    subtotal_cents = Column(Integer, nullable=False, default=0)
    fee_cents = Column(Integer, nullable=False, default=0)
    total_cents = Column(Integer, nullable=False, default=0)
    payment_provider = Column(String(30), default="clover")
    payment_id = Column(String(255), nullable=True, unique=True)
    clover_checkout_id = Column(String(255), nullable=True, unique=True, index=True)
    items_json = Column(Text, nullable=True)
    payment_status = Column(String(30), default="pending")  # pending|paid|failed|refunded|partial_refund
    receipt_number = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

class IssuedTicket(Base):
    __tablename__ = "issued_tickets"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("ticket_orders.id", ondelete="CASCADE"), index=True, nullable=False)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    ticket_type_id = Column(Integer, ForeignKey("event_ticket_types.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("event_sellers.id"), index=True, nullable=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    qr_token_hash = Column(String(128), unique=True, nullable=False, index=True)
    qr_token_encrypted = Column(Text, nullable=True)
    status = Column(String(20), default="valid", index=True)  # valid|used|void|refunded
    price_cents = Column(Integer, nullable=False)
    commission_cents = Column(Integer, nullable=False, default=0)
    attendee_name = Column(String(160), nullable=True)
    attendee_email = Column(String(255), nullable=True)
    issued_at = Column(DateTime, default=datetime.utcnow)
    scanned_at = Column(DateTime, nullable=True)
    scanned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class TicketScanLog(Base):
    __tablename__ = "ticket_scan_logs"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("issued_tickets.id", ondelete="CASCADE"), index=True, nullable=False)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    scanned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    result = Column(String(30), nullable=False)  # admitted|already_used|invalid|wrong_event|void|refunded
    device_label = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TicketDelivery(Base):
    __tablename__ = "ticket_deliveries"
    __table_args__ = (UniqueConstraint("order_id", "channel", name="uq_ticket_delivery_channel"),)
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("ticket_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    provider_id = Column(String(255), nullable=True)
    last_error = Column(String(255), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    next_attempt_at = Column(DateTime, nullable=True, default=datetime.utcnow)

class TicketRecovery(Base):
    __tablename__ = "ticket_recoveries"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("ticket_orders.id"), nullable=False, unique=True)
    clover_order_id = Column(String(255), nullable=False, unique=True)
    payment_ids_json = Column(Text, nullable=False)
    verified_total_cents = Column(Integer, nullable=False)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class TicketCheckoutAttempt(Base):
    __tablename__ = "ticket_checkout_attempts"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("ticket_orders.id"), nullable=False, unique=True)
    checkout_id = Column(String(255), nullable=False, unique=True)
    checkout_url = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class SellerPayout(Base):
    __tablename__ = "seller_payouts"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id", ondelete="CASCADE"), index=True, nullable=False)
    seller_id = Column(Integer, ForeignKey("event_sellers.id"), index=True, nullable=False)
    gross_sales_cents = Column(Integer, nullable=False, default=0)
    commission_earned_cents = Column(Integer, nullable=False, default=0)
    amount_paid_cents = Column(Integer, nullable=False, default=0)
    status = Column(String(20), default="unpaid")  # unpaid|partial|paid
    paid_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PaperTicketBatch(Base):
    __tablename__ = "paper_ticket_batches"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("boxing_events.id"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("event_sellers.id"), nullable=False, index=True)
    ticket_type_id = Column(Integer, ForeignKey("event_ticket_types.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    commission_cents = Column(Integer, nullable=False)
    request_key = Column(String(36), unique=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class PaperTicket(Base):
    __tablename__ = "paper_tickets"
    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("paper_ticket_batches.id"), nullable=False, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    qr_token_hash = Column(String(128), unique=True, nullable=False, index=True)
    qr_token_encrypted = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="allocated")  # allocated|sold|returned
    order_id = Column(Integer, ForeignKey("ticket_orders.id"), unique=True, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    returned_at = Column(DateTime, nullable=True)
