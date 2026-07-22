from dotenv import load_dotenv
import os
import logging
from .services.memberships import (
    apply_membership,
    is_event_product,
    is_membership_product,
    recalculate_member_from_payments,
)
logger = logging.getLogger(__name__)
load_dotenv(override=True)
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64, io, qrcode
from openai import OpenAI
import resend
import json
import requests
import uuid
import resend
import html
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File
import shutil
import re
from .operations.router import router as operations_router
from pydantic import BaseModel, EmailStr, Field

from .services.password_reset_service import (
    create_password_reset_token,
    send_password_reset_email,
    verify_password_reset_token,
)
from sqlalchemy import text
from .database import Base, engine, get_db
from .services.sms_service import send_sms
from .models import (
    User,
    SalesRep,
    Member,
    MembershipProduct,
    Sale,
    CloverSetting,
    Lead,
    WaiverSubmission,
    Attendance,
    MerchandiseCheckout,
    SecurityLog,
    MarketingContact,
    MarketingCampaign,
    MarketingTemplate,
)
from .schemas import (
    LoginIn,
    RepCreate,
    SaleCreate,
    LeadCreate,
    WaiverSubmissionCreate,
)

from .auth import verify_password, hash_password, create_token, decode_token
from .core.dependencies import current_user
from .core.permissions import require_admin, require_admin_or_staff
from .commission import commission_rate
from sqlalchemy import or_
import sqlite3
import pandas as pd
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")



client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
resend.api_key = os.getenv("RESEND_API_KEY")

Base.metadata.create_all(bind=engine)

def add_column_if_missing(table, column, column_type):
    with engine.connect() as conn:
        existing = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        columns = [row[1] for row in existing]

        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
            conn.commit()

def run_sqlite_migrations():
    add_column_if_missing("members", "member_number", "VARCHAR")
    add_column_if_missing("members", "barcode", "VARCHAR")
    add_column_if_missing("members", "membership_start", "DATETIME")
    add_column_if_missing("members", "membership_end", "DATETIME")
    add_column_if_missing("members", "membership_status", "VARCHAR")
    add_column_if_missing("members", "auto_renew", "BOOLEAN DEFAULT 0")
    add_column_if_missing("members", "assigned_coach", "VARCHAR")
    add_column_if_missing("members", "waiver_signed", "BOOLEAN DEFAULT 0")



    add_column_if_missing("sales", "clover_checkout_id", "VARCHAR")
    add_column_if_missing("sales", "transaction_status", "VARCHAR")
    add_column_if_missing("sales", "refunded", "BOOLEAN DEFAULT 0")
    add_column_if_missing("sales", "refund_amount", "FLOAT DEFAULT 0")
    add_column_if_missing("sales", "payment_method", "VARCHAR")
    add_column_if_missing("membership_products", "category", "VARCHAR")
    add_column_if_missing("members", "member_type", "VARCHAR DEFAULT 'MEMBER'")

    add_column_if_missing("leads", "clover_checkout_id", "VARCHAR")
    add_column_if_missing("leads", "paid_at", "DATETIME")
    add_column_if_missing("leads", "converted_at", "DATETIME")
    add_column_if_missing("leads", "conversion_source", "VARCHAR")
    add_column_if_missing("leads", "address", "VARCHAR")
    add_column_if_missing("leads", "city", "VARCHAR")
    add_column_if_missing("leads", "state", "VARCHAR")
    add_column_if_missing("leads", "zip_code", "VARCHAR")
    add_column_if_missing("members", "address", "VARCHAR")
    add_column_if_missing("members", "city", "VARCHAR")
    add_column_if_missing("members", "state", "VARCHAR")
    add_column_if_missing("members", "zip_code", "VARCHAR")
    add_column_if_missing("members", "digital_member_id", "VARCHAR")
    add_column_if_missing("members", "qr_code", "VARCHAR")
    add_column_if_missing("members", "photo_url", "VARCHAR")
    add_column_if_missing("members", "date_of_birth", "DATETIME")
    add_column_if_missing("members", "emergency_contact", "VARCHAR")
    add_column_if_missing("members", "emergency_phone", "VARCHAR")
    add_column_if_missing("members", "membership_type", "VARCHAR")
    add_column_if_missing("members", "membership_level", "VARCHAR")
    add_column_if_missing("members", "last_checkin", "DATETIME")
    add_column_if_missing("members", "checkins", "INTEGER DEFAULT 0")
    add_column_if_missing("members", "total_checkins", "INTEGER DEFAULT 0")
    add_column_if_missing("members", "expires_soon", "BOOLEAN DEFAULT 0")
    add_column_if_missing("members", "notes", "VARCHAR")
    add_column_if_missing("members", "billing_cycle", "VARCHAR")
    add_column_if_missing("members", "monthly_rate", "FLOAT DEFAULT 0")
    add_column_if_missing("members", "next_billing_date", "DATETIME")
    add_column_if_missing("members", "autopay_enabled", "BOOLEAN DEFAULT 0")
    add_column_if_missing("members", "billing_status", "VARCHAR")
    add_column_if_missing("members", "clover_subscription_id", "VARCHAR")
    add_column_if_missing("members", "last_payment_date", "DATETIME")
    add_column_if_missing("members", "past_due_amount", "FLOAT DEFAULT 0")
    add_column_if_missing("membership_products", "category", "VARCHAR")
    add_column_if_missing("membership_products", "is_membership", "BOOLEAN DEFAULT 0")
    add_column_if_missing("membership_products", "renews_monthly", "BOOLEAN DEFAULT 0")
    add_column_if_missing("membership_products", "autopay_allowed", "BOOLEAN DEFAULT 0")
    add_column_if_missing("membership_products", "default_membership_months", "INTEGER DEFAULT 1")
    add_column_if_missing("membership_products", "sku", "VARCHAR")
    add_column_if_missing("membership_products", "stock_quantity", "INTEGER DEFAULT 0")
    add_column_if_missing("membership_products", "track_inventory", "BOOLEAN DEFAULT 0")
    add_column_if_missing("sales", "quantity", "INTEGER DEFAULT 1")
    add_column_if_missing("sales", "unit_price", "FLOAT DEFAULT 0")
    add_column_if_missing("sales", "sale_type", "VARCHAR DEFAULT 'membership'")
    with engine.connect() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            checkin_time DATETIME,
            checkout_time DATETIME,
            method VARCHAR,
            location VARCHAR,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
        """))
        conn.commit()

run_sqlite_migrations()
app = FastAPI(title="TNG CRM 2.0")

app.include_router(operations_router)
os.makedirs("uploads/members", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware(
    CORSMiddleware,
allow_origins=[
    "https://goldfish-app-jq38z.ondigitalocean.app",
    "https://tngos.tngboxinggym.com",
    "https://display.tngboxinggym.com",
    "https://crm.tngboxinggym.com",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_admin():
    db = next(get_db())
    try:
        existing = (
            db.query(User)
            .filter(User.email == "admin@tngboxinggym.com")
            .first()
        )

        if not existing:
            admin = User(
                name="TNG Admin",
                email="admin@tngboxinggym.com",
                password_hash=hash_password("admin123"),
                role="admin",
                active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
def validate_new_password(password: str) -> None:
    if len(password) < 12:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 12 characters.",
        )

    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must include an uppercase letter.",
        )

    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must include a lowercase letter.",
        )

    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="Password must include a number.",
        )

    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must include a symbol.",
        )

Base.metadata.create_all(bind=engine)
def ensure_security_schema():
    database_path = engine.url.database

    if not database_path:
        raise RuntimeError("Could not determine SQLite database path")

    connection = sqlite3.connect(database_path)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR NOT NULL,
                description VARCHAR,
                ip_address VARCHAR,
                endpoint VARCHAR,
                success BOOLEAN DEFAULT 1,
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if "failed_login_attempts" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0
                """
            )

        if "locked_until" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN locked_until DATETIME
                """
            )

        if "last_login" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN last_login DATETIME
                """
            )

        if "last_login_ip" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE users
                ADD COLUMN last_login_ip VARCHAR
                """
            )

        connection.commit()
    finally:
        connection.close()





ensure_security_schema()
seed_admin()
@app.post("/api/login")
def login(
    data: LoginIn,
    request: Request,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()
    ip_address = request.client.host if request.client else "unknown"
    now = datetime.utcnow()

    user = db.query(User).filter(User.email == email).first()

    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked. Try again later.",
        )

    if not user or not verify_password(data.password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)

        security_log = SecurityLog(
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            description=f"Failed login attempt for {email}",
            ip_address=ip_address,
            endpoint="/api/login",
            success=False,
        )

        db.add(security_log)
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now
    user.last_login_ip = ip_address

    security_log = SecurityLog(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        description=f"{user.name} logged in",
        ip_address=ip_address,
        endpoint="/api/login",
        success=True,
    )

    db.add(security_log)
    db.commit()

    return {
        "token": create_token(
            {
                "sub": str(user.id),
                "role": user.role,
            }
        ),
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str

@app.post("/api/auth/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    generic_response = {
        "message": (
            "If an account exists for that email, "
            "a password reset link has been sent."
        )
    }

    normalized_email = data.email.strip().lower()

    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )

    if not user or user.active is False:
        return generic_response

    try:
        reset_token = create_password_reset_token(
            user_id=user.id,
            password_hash=user.password_hash,
        )

        send_password_reset_email(
            recipient_email=user.email,
            recipient_name=user.name or "",
            token=reset_token,
        )
    except Exception:
        logger.exception(
            "Password reset email failed for user ID %s",
            user.id,
        )

    return generic_response

@app.post("/api/auth/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    validate_new_password(data.password)

    try:
        encoded_payload = data.token.split(".", 1)[0]

        padding = "=" * (-len(encoded_payload) % 4)

        token_payload = json.loads(
            base64.urlsafe_b64decode(
                encoded_payload + padding
            ).decode("utf-8")
        )

        user_id = int(token_payload.get("user_id"))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=400,
            detail="The password reset link is invalid or expired.",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="The password reset link is invalid or expired.",
        )

    verified_payload = verify_password_reset_token(
        token=data.token,
        password_hash=user.password_hash,
    )

    if not verified_payload:
        raise HTTPException(
            status_code=400,
            detail="The password reset link is invalid or expired.",
        )

    user.password_hash = hash_password(data.password)
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()

    return {
        "message": (
            "Your password was reset successfully. "
            "You may now sign in."
        )
    }

@app.get("/api/security/overview")
def security_overview(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    failed_logins = (
        db.query(SecurityLog)
        .filter(SecurityLog.action == "LOGIN_FAILED")
        .count()
    )

    successful_logins = (
        db.query(SecurityLog)
        .filter(SecurityLog.action == "LOGIN_SUCCESS")
        .count()
    )

    locked_accounts = (
        db.query(User)
        .filter(User.locked_until != None)
        .count()
    )

    recent = (
        db.query(SecurityLog)
        .order_by(SecurityLog.created_at.desc())
        .limit(25)
        .all()
    )

    return {
        "security_score": 95,
        "failed_logins": failed_logins,
        "successful_logins": successful_logins,
        "locked_accounts": locked_accounts,
        "recent_events": [
            {
                "time": log.created_at.isoformat() if log.created_at else None,
                "action": log.action,
                "description": log.description,
                "ip": log.ip_address,
                "success": log.success,
            }
            for log in recent
        ],
    }
@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


@app.post("/api/reps")
def create_rep(data: RepCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role="rep")
    db.add(new_user); db.flush()
    rep = SalesRep(user_id=new_user.id, phone=data.phone, referral_slug=data.referral_slug, clover_link=data.clover_link)
    db.add(rep); db.commit(); db.refresh(rep)
    return {"id": rep.id, "name": new_user.name, "email": new_user.email, "temporary_password": data.password, "referral_url": f"/join/{rep.referral_slug}"}

@app.get("/api/reps")
def list_reps(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    reps = db.query(SalesRep).all()
    return [{"id": r.id, "name": r.user.name, "email": r.user.email, "phone": r.phone, "slug": r.referral_slug, "clover_link": r.clover_link} for r in reps]

@app.post("/api/staff")
def create_staff(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Name, email, and password are required",
        )

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    staff_user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="staff",
    )

    db.add(staff_user)
    db.commit()
    db.refresh(staff_user)

    return {
        "id": staff_user.id,
        "name": staff_user.name,
        "email": staff_user.email,
        "role": staff_user.role,
        "message": "Staff account created",
    }

@app.get("/api/reps/me")
def my_rep_profile(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != "rep" or not user.rep_profile:
        raise HTTPException(status_code=404, detail="Sales rep profile not found")

    rep = user.rep_profile

    return {
        "id": rep.id,
        "name": user.name,
        "email": user.email,
        "phone": rep.phone,
        "slug": rep.referral_slug,
        "referral_url": f"https://tngos.tngboxinggym.com?join={rep.referral_slug}",
    }


@app.get("/api/reps/me/qr")
def my_rep_qr(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if user.role != "rep" or not user.rep_profile:
        raise HTTPException(status_code=404, detail="Sales rep profile not found")

    rep = user.rep_profile
    url = f"https://tngos.tngboxinggym.com?join={rep.referral_slug}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return {
        "rep_id": rep.id,
        "name": user.name,
        "slug": rep.referral_slug,
        "url": url,
        "qr_png_base64": base64.b64encode(buf.getvalue()).decode(),
    }


@app.get("/api/reps/{rep_id}/qr")
def rep_qr(rep_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rep = db.query(SalesRep).filter(SalesRep.id == rep_id).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Rep not found")
    if user.role != "admin" and (not user.rep_profile or user.rep_profile.id != rep_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    url = f"https://goldfish-app-jq38z.ondigitalocean.app?join={rep.referral_slug}"
    img = qrcode.make(url)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return {"url": url, "qr_png_base64": base64.b64encode(buf.getvalue()).decode()}




def is_membership_sale(sale):
    if not sale:
        return False

    if not is_membership_product(sale.product):
        return False

    amount = round(float(sale.amount or 0), 2)

    if amount in EVENT_TICKET_AMOUNTS:
        return False

    return sale.payment_status == "paid"

@app.post("/api/sales")
def create_sale(data: SaleCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role == "rep" and user.rep_profile.id != data.sales_rep_id:
        raise HTTPException(status_code=403, detail="Reps can only create their own sales")

    product = db.query(MembershipProduct).filter(MembershipProduct.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")



    member = Member(
        first_name=data.member_first_name,
        last_name=data.member_last_name,
        email=data.member_email,
        phone=data.member_phone,
        status="active" if data.payment_status == "paid" else "pending",
        membership_status="active" if data.payment_status == "paid" else "pending",
            )
    if data.payment_status == "paid":

            apply_membership(
                member,
                product,
                purchase_date=sale_date,
            )
    else:
        member.membership_status = "pending"
        member.billing_status = "pending"
    db.add(member)
    db.flush()

    sale = Sale(
        member_id=member.id,
        sales_rep_id=data.sales_rep_id,
        product_id=product.id,
        amount=product.price,
        payment_status=data.payment_status,
        clover_order_id=data.clover_order_id,
        clover_payment_id=data.clover_payment_id,
        sale_date=datetime.utcnow(),
    )

    db.add(sale)
    db.commit()
    db.refresh(sale)

    return {
        "sale_id": sale.id,
        "amount": sale.amount,
        "status": sale.payment_status,
        "membership_end": member.membership_end.isoformat() if member.membership_end else None,
        "billing_cycle": member.billing_cycle,
    }

@app.get("/api/leaderboard")
def leaderboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    now = datetime.utcnow()
    rows = db.query(SalesRep.id, User.name, func.count(Sale.id), func.sum(Sale.amount)).join(User).outerjoin(Sale).filter((Sale.id == None) | ((extract('month', Sale.sale_date) == now.month) & (extract('year', Sale.sale_date) == now.year))).group_by(SalesRep.id, User.name).all()
    return [{"rep_id": r[0], "name": r[1], "sales": r[2] or 0, "revenue": float(r[3] or 0), "rate": commission_rate(r[2] or 0)} for r in rows]

@app.get("/api/join/front-desk")
def front_desk_join_page_data(db: Session = Depends(get_db)):
    products = (
        db.query(MembershipProduct)
        .filter(
            MembershipProduct.active == True,
            MembershipProduct.is_membership == True,
        )
        .order_by(MembershipProduct.name.asc())
        .all()
    )

    return {
        "rep_id": None,
        "rep_name": "TNG Boxing",
        "clover_link": "",
        "registration_source": "front_desk",
        "products": products,
    }


@app.get("/api/join/{slug}")
def join_page_data(slug: str, db: Session = Depends(get_db)):
    rep = (
        db.query(SalesRep)
        .filter(SalesRep.referral_slug == slug)
        .first()
    )

    if not rep:
        raise HTTPException(
            status_code=404,
            detail="Rep link not found",
        )

    products = (
        db.query(MembershipProduct)
        .filter(
            MembershipProduct.active == True,
            MembershipProduct.is_membership == True,
        )
        .order_by(MembershipProduct.name.asc())
        .all()
    )

    return {
        "rep_id": rep.id,
        "rep_name": rep.user.name,
        "clover_link": rep.clover_link,
        "registration_source": "sales_rep",
        "products": products,
    }

@app.get("/api/members")
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    cutoff_date = datetime(2026, 7, 20, 23, 59, 59)

    paid_sale_member_ids = (
        db.query(Sale.member_id)
        .filter(
            Sale.payment_status == "paid",
            Sale.member_id != None,
        )
        .distinct()
        .subquery()
    )

    members = (
        db.query(Member)
        .filter(
            Member.id.in_(
                db.query(paid_sale_member_ids.c.member_id)
            )
        )
        .order_by(
            Member.last_name.asc(),
            Member.first_name.asc(),
        )
        .all()
    )

    results = []

    for member in members:
        recalculate_member_from_payments(member, db)

        # Exclude memberships expiring July 20, 2026 or earlier.
        if (
            member.membership_end
            and member.membership_end <= cutoff_date
        ):
            continue

        results.append({
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "phone": member.phone,
            "status": member.status,
            "member_number": member.member_number,
            "barcode": member.barcode,
            "qr_code": member.qr_code,
            "digital_member_id": member.digital_member_id,
            "membership_type": member.membership_type,
            "membership_status": member.membership_status,
            "membership_start": (
                member.membership_start.isoformat()
                if member.membership_start
                else None
            ),
            "membership_end": (
                member.membership_end.isoformat()
                if member.membership_end
                else None
            ),
            "last_payment_date": (
                member.last_payment_date.isoformat()
                if member.last_payment_date
                else None
            ),
            "next_billing_date": (
                member.next_billing_date.isoformat()
                if member.next_billing_date
                else None
            ),
            "billing_status": member.billing_status,
            "clover_customer_id": member.clover_customer_id,
            "last_checkin": (
                member.last_checkin.isoformat()
                if member.last_checkin
                else None
            ),
            "total_checkins": member.total_checkins or 0,
            "photo_url": member.photo_url,
            "created_at": (
                member.created_at.isoformat()
                if member.created_at
                else None
            ),
        })

    db.commit()

    return results

@app.post("/api/products")
def create_product(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    name = (data.get("name") or "").strip()
    price = float(data.get("price") or 0)
    category = (data.get("category") or "other").strip().lower()

    if not name:
        raise HTTPException(status_code=400, detail="Product name is required")
    if price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")

    existing = db.query(MembershipProduct).filter(
        func.lower(MembershipProduct.name) == name.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A product with this name already exists")

    product = MembershipProduct(
        name=name,
        price=price,
        category=category,
        active=bool(data.get("active", True)),
        is_membership=bool(data.get("is_membership", category == "membership")),
        renews_monthly=bool(data.get("renews_monthly", False)),
        autopay_allowed=bool(data.get("autopay_allowed", False)),
        default_membership_months=int(data.get("default_membership_months") or 1),
        sku=(data.get("sku") or "").strip() or None,
        stock_quantity=max(0, int(data.get("stock_quantity") or 0)),
        track_inventory=bool(data.get("track_inventory", category == "merchandise")),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def finalize_merchandise_checkout(
    checkout: MerchandiseCheckout,
    payment_id: str,
    order_id: str,
    db: Session,
):
    if checkout.status == "paid":
        return checkout

    cart = json.loads(checkout.cart_json or "[]")
    if not cart:
        raise HTTPException(status_code=400, detail="Merchandise cart is empty")

    member = None
    if checkout.customer_email:
        member = db.query(Member).filter(
            func.lower(Member.email) == checkout.customer_email.lower()
        ).first()
    if not member and checkout.customer_phone:
        member = db.query(Member).filter(
            Member.phone == checkout.customer_phone
        ).first()

    if not member:
        name_parts = checkout.customer_name.split(maxsplit=1)
        member = Member(
            first_name=name_parts[0] if name_parts else "Retail",
            last_name=name_parts[1] if len(name_parts) > 1 else "Customer",
            email=checkout.customer_email or "",
            phone=checkout.customer_phone or "",
            status="customer",
            membership_status="not_applicable",
            membership_type="Merchandise Customer",
            member_type="CUSTOMER",
        )
        db.add(member)
        db.flush()

    for item in cart:
        product = db.query(MembershipProduct).filter(
            MembershipProduct.id == int(item["product_id"])
        ).first()
        quantity = max(1, int(item.get("quantity") or 1))

        if not product or product.category != "merchandise":
            raise HTTPException(status_code=400, detail="Invalid merchandise product")

        if product.track_inventory:
            available = int(product.stock_quantity or 0)
            if available < quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Only {available} of {product.name} remain in stock",
                )
            product.stock_quantity = available - quantity

        unit_price = float(product.price or 0)
        sale = Sale(
            member_id=member.id,
            sales_rep_id=checkout.sales_rep_id,
            product_id=product.id,
            amount=unit_price * quantity,
            payment_status="paid",
            transaction_status="paid",
            payment_method="clover",
            clover_checkout_id=checkout.clover_checkout_id,
            clover_payment_id=payment_id or "",
            clover_order_id=order_id or "",
            sale_date=datetime.utcnow(),
            quantity=quantity,
            unit_price=unit_price,
            sale_type="merchandise",
        )
        db.add(sale)

    checkout.status = "paid"
    checkout.clover_payment_id = payment_id or ""
    checkout.clover_order_id = order_id or ""
    checkout.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(checkout)
    return checkout


@app.post("/api/merchandise-checkouts")
def create_merchandise_checkout(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    customer_name = (data.get("customer_name") or "").strip()
    customer_email = (data.get("customer_email") or "").strip().lower()
    customer_phone = (data.get("customer_phone") or "").strip()
    requested_cart = data.get("cart") or []

    if not customer_name:
        raise HTTPException(status_code=400, detail="Customer name is required")
    if not isinstance(requested_cart, list) or not requested_cart:
        raise HTTPException(status_code=400, detail="Add merchandise to the cart")

    if user.role == "rep":
        rep = user.rep_profile
        if not rep:
            raise HTTPException(status_code=403, detail="Sales rep profile not found")
    else:
        rep_id = data.get("sales_rep_id")
        rep = (
            db.query(SalesRep).filter(SalesRep.id == rep_id).first()
            if rep_id
            else db.query(SalesRep).first()
        )
        if not rep:
            raise HTTPException(status_code=400, detail="No sales rep is available")

    clean_cart = []
    line_items = []
    total = 0.0

    for requested in requested_cart:
        product_id = int(requested.get("product_id") or 0)
        quantity = max(1, int(requested.get("quantity") or 1))
        product = db.query(MembershipProduct).filter(
            MembershipProduct.id == product_id
        ).first()

        if not product or product.category != "merchandise" or not product.active:
            raise HTTPException(status_code=400, detail="Invalid merchandise product")

        if product.track_inventory and int(product.stock_quantity or 0) < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Only {int(product.stock_quantity or 0)} of {product.name} are in stock",
            )

        unit_price = float(product.price or 0)
        clean_cart.append({"product_id": product.id, "quantity": quantity})
        line_items.append({
            "name": product.name,
            "note": product.sku or "TNG merchandise",
            "price": int(round(unit_price * 100)),
            "unitQty": quantity,
        })
        total += unit_price * quantity

    checkout = MerchandiseCheckout(
        sales_rep_id=rep.id,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        cart_json=json.dumps(clean_cart),
        total_amount=total,
        status="pending",
    )
    db.add(checkout)
    db.commit()
    db.refresh(checkout)

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")

    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(status_code=500, detail="Clover credentials missing")

    base_url = (
        "https://api.clover.com"
        if clover_env == "production"
        else "https://apisandbox.dev.clover.com"
    )
    app_url = os.getenv("TNG_APP_URL", "https://tngos.tngboxinggym.com").rstrip("/")

    customer_parts = customer_name.split(maxsplit=1)
    customer = {
        "firstName": customer_parts[0] if customer_parts else "Customer",
        "lastName": customer_parts[1] if len(customer_parts) > 1 else "",
    }
    if customer_email:
        customer["email"] = customer_email
    if customer_phone:
        customer["phoneNumber"] = customer_phone

    payload = {
        "customer": customer,
        "redirectUrls": {
            "success": f"{app_url}/?merch_payment=success&checkout_ref={checkout.id}",
            "failure": f"{app_url}/?merch_payment=failure&checkout_ref={checkout.id}",
        },
        "shoppingCart": {"lineItems": line_items},
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "X-Clover-Merchant-Id": merchant_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    response = requests.post(
        f"{base_url}/invoicingcheckoutservice/v1/checkouts",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        checkout.status = "checkout_error"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Clover checkout error {response.status_code}: {response.text}",
        )

    clover_data = response.json()
    checkout.clover_checkout_id = (
        clover_data.get("checkoutSessionId")
        or clover_data.get("id")
    )
    db.commit()

    checkout_url = clover_data.get("href") or clover_data.get("url")
    if not checkout_url:
        raise HTTPException(status_code=500, detail="Clover did not return a checkout URL")

    return {
        "checkout_id": checkout.id,
        "clover_checkout_id": checkout.clover_checkout_id,
        "checkout_url": checkout_url,
        "total": checkout.total_amount,
        "status": checkout.status,
    }


@app.get("/api/merchandise-checkouts/{checkout_id}")
def get_merchandise_checkout(
    checkout_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    checkout = db.query(MerchandiseCheckout).filter(
        MerchandiseCheckout.id == checkout_id
    ).first()
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found")
    if user.role == "rep" and (
        not user.rep_profile or checkout.sales_rep_id != user.rep_profile.id
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    return {
        "id": checkout.id,
        "status": checkout.status,
        "total": checkout.total_amount,
        "clover_checkout_id": checkout.clover_checkout_id,
        "paid_at": checkout.paid_at.isoformat() if checkout.paid_at else None,
    }

@app.get("/api/sales")
def list_sales(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Sale)

    if user.role == "rep":
        if not user.rep_profile:
            return []
        query = query.filter(Sale.sales_rep_id == user.rep_profile.id)

    sales = query.order_by(Sale.sale_date.desc()).all()
    results = []

    for sale in sales:
        rep = sale.sales_rep
        member = sale.member
        product = sale.product
        category = product.category if product and product.category else "other"

        results.append({
            "id": sale.id,
            "member": f"{member.first_name} {member.last_name}" if member else "",
            "rep": rep.user.name if rep and rep.user else "",
            "membership": product.name if product else "",
            "product": product.name if product else "",
            "category": category,
            "sale_type": sale.sale_type or ("merchandise" if category == "merchandise" else "membership"),
            "quantity": sale.quantity or 1,
            "unit_price": sale.unit_price or (sale.amount or 0),
            "amount": sale.amount,
            "payment_status": sale.payment_status,
            "payment_method": sale.payment_method,
            "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
            "clover_payment_id": sale.clover_payment_id,
        })

    return results
@app.get("/api/my-dashboard")
def my_dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = datetime.utcnow()

    if user.role == "admin":
        rep = db.query(SalesRep).first()
    else:
        rep = user.rep_profile

    if not rep:
        return {
            "rep_name": user.name,
            "sales_this_month": 0,
            "revenue": 0,
            "commission_rate": 0,
            "commission_earned": 0,
            "next_tier": "No sales rep profile found",
            "referral_url": "",
            "recent_sales": []
        }

    q = db.query(Sale).filter(
        Sale.sales_rep_id == rep.id,
        extract("month", Sale.sale_date) == now.month,
        extract("year", Sale.sale_date) == now.year
    )

    sales = q.all()
    count = len(sales)
    revenue = sum(s.amount for s in sales)
    rate = commission_rate(count)

    if count < 10:
        next_tier = f"{10 - count} more sales until 20%"
    elif count < 20:
        next_tier = f"{20 - count} more sales until 25%"
    else:
        next_tier = "Max tier reached"

    recent_sales = []
    for s in sales[-5:]:
        member = db.query(Member).filter(Member.id == s.member_id).first()
        product = db.query(MembershipProduct).filter(MembershipProduct.id == s.product_id).first()

        recent_sales.append({
            "member": f"{member.first_name} {member.last_name}" if member else "",
            "membership": product.name if product else "",
            "amount": s.amount,
            "date": s.sale_date.isoformat() if s.sale_date else None
        })

    return {
        "rep_name": rep.user.name,
        "sales_this_month": count,
        "revenue": revenue,
        "commission_rate": rate,
        "commission_earned": revenue * rate,
        "next_tier": next_tier,
        "referral_slug": rep.referral_slug,
        "referral_url": f"https://goldfish-app-jq38z.ondigitalocean.app?join={rep.referral_slug}",
        "recent_sales": recent_sales
    }

@app.post("/api/leads")
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    rep = None

    if data.referral_slug:
        rep = (
            db.query(SalesRep)
            .filter(SalesRep.referral_slug == data.referral_slug)
            .first()
        )

    lead = Lead(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=data.email.strip().lower(),
        phone=(data.phone or "").strip(),

        # NEW ADDRESS FIELDS
        address=(data.address or "").strip(),
        city=(data.city or "").strip(),
        state=(data.state or "").strip().upper(),
        zip_code=(data.zip_code or "").strip(),

        product_id=data.product_id,
        sales_rep_id=rep.id if rep else None,
        referral_slug=data.referral_slug,
        status="new",
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "id": lead.id,
        "status": lead.status,
        "message": "Lead created",
    }
@app.get("/api/leads")
def list_leads(db: Session = Depends(get_db), user: User = Depends(current_user)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    results = []

    for lead in leads:
        product = db.query(MembershipProduct).filter(MembershipProduct.id == lead.product_id).first()
        rep = db.query(SalesRep).filter(SalesRep.id == lead.sales_rep_id).first()

        results.append({
            "id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "phone": lead.phone,
            "membership": product.name if product else "",
            "rep": rep.user.name if rep and rep.user else "",
            "status": lead.status,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        })

    return results
WAIVER_VERSION = "2026-07-18-v1"

WAIVER_TEXT = """
I understand that boxing, fitness training, sparring, strength training,
conditioning, and related activities involve inherent risks of injury.

I voluntarily choose to participate and accept all risks associated with
participation. I confirm that the participant is physically able to take
part in these activities and will disclose any relevant medical condition
to TNG Boxing staff.

I release and hold harmless TNG Boxing, TNG Foundation, their owners,
employees, coaches, volunteers, representatives, and affiliates from claims
arising from ordinary risks associated with participation, except where
prohibited by law.

I authorize TNG Boxing staff to contact emergency services when reasonably
necessary. I understand that I am responsible for medical expenses incurred
for the participant.

By signing electronically, I confirm that I have read, understood, and
accepted this waiver.
""".strip()


@app.post("/api/waiver-submissions")
def create_waiver_submission(
    data: WaiverSubmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == data.lead_id).first()

    if not lead:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    if not data.waiver_accepted:
        raise HTTPException(
            status_code=400,
            detail="Waiver acceptance is required",
        )

    if not data.medical_acknowledgment:
        raise HTTPException(
            status_code=400,
            detail="Medical acknowledgment is required",
        )

    if not data.signature_name.strip():
        raise HTTPException(
            status_code=400,
            detail="Electronic signature is required",
        )

    existing = (
        db.query(WaiverSubmission)
        .filter(WaiverSubmission.lead_id == lead.id)
        .order_by(WaiverSubmission.submitted_at.desc())
        .first()
    )

    now = datetime.utcnow()
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    if existing:
        existing.participant_first_name = data.participant_first_name.strip()
        existing.participant_last_name = data.participant_last_name.strip()
        existing.participant_date_of_birth = data.participant_date_of_birth
        existing.guardian_name = (
            data.guardian_name.strip()
            if data.guardian_name
            else None
        )
        existing.signer_relationship = data.signer_relationship
        existing.emergency_contact_name = data.emergency_contact_name.strip()
        existing.emergency_contact_phone = data.emergency_contact_phone.strip()
        existing.waiver_accepted = data.waiver_accepted
        existing.medical_acknowledgment = data.medical_acknowledgment
        existing.waiver_version = WAIVER_VERSION
        existing.waiver_text_snapshot = WAIVER_TEXT
        existing.signature_name = data.signature_name.strip()
        existing.signature_data = data.signature_data
        existing.photo_release = data.photo_release
        existing.sms_consent = data.sms_consent
        existing.sms_consent_at = now if data.sms_consent else None
        existing.sms_disclosure_version = (
            WAIVER_VERSION if data.sms_consent else None
        )
        existing.email_consent = data.email_consent
        existing.email_consent_at = now if data.email_consent else None
        existing.email_disclosure_version = (
            WAIVER_VERSION if data.email_consent else None
        )
        existing.signed_at = now
        existing.submitted_at = now
        existing.ip_address = ip_address
        existing.user_agent = user_agent

        waiver = existing
    else:
        waiver = WaiverSubmission(
            lead_id=lead.id,
            participant_first_name=data.participant_first_name.strip(),
            participant_last_name=data.participant_last_name.strip(),
            participant_date_of_birth=data.participant_date_of_birth,
            guardian_name=(
                data.guardian_name.strip()
                if data.guardian_name
                else None
            ),
            signer_relationship=data.signer_relationship,
            emergency_contact_name=data.emergency_contact_name.strip(),
            emergency_contact_phone=data.emergency_contact_phone.strip(),
            waiver_accepted=data.waiver_accepted,
            medical_acknowledgment=data.medical_acknowledgment,
            waiver_version=WAIVER_VERSION,
            waiver_text_snapshot=WAIVER_TEXT,
            signature_name=data.signature_name.strip(),
            signature_data=data.signature_data,
            photo_release=data.photo_release,
            sms_consent=data.sms_consent,
            sms_consent_at=now if data.sms_consent else None,
            sms_disclosure_version=(
                WAIVER_VERSION if data.sms_consent else None
            ),
            email_consent=data.email_consent,
            email_consent_at=now if data.email_consent else None,
            email_disclosure_version=(
                WAIVER_VERSION if data.email_consent else None
            ),
            signed_at=now,
            submitted_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
            submission_uuid=str(uuid.uuid4()),
        )

        db.add(waiver)

    lead.status = "waiver_completed"
    db.commit()
    db.refresh(waiver)

    return {
        "id": waiver.id,
        "lead_id": waiver.lead_id,
        "status": "completed",
        "submission_uuid": waiver.submission_uuid,
        "message": "Waiver and consent information saved",
    }



@app.post("/api/clover/create-checkout/{lead_id}")
def create_clover_checkout(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    product = (
        db.query(MembershipProduct)
        .filter(MembershipProduct.id == lead.product_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=404,
            detail="Membership product not found",
        )

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(
            status_code=500,
            detail="Clover credentials missing",
        )

    base_url = (
        "https://api.clover.com"
        if clover_env == "production"
        else "https://apisandbox.dev.clover.com"
    )

    payload = {
        "customer": {
            "firstName": lead.first_name,
            "lastName": lead.last_name,
            "email": lead.email,
            "phoneNumber": lead.phone or "",
        },
        "shoppingCart": {
            "lineItems": [
                {
                    "name": product.name,
                    "price": int(product.price * 100),
                    "unitQty": 1,
                }
            ]
        },
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "X-Clover-Merchant-Id": merchant_id,
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{base_url}/invoicingcheckoutservice/v1/checkouts",
        json=payload,
        headers=headers,
        timeout=20,
    )

    print("========== CLOVER RESPONSE ==========")
    print(response.status_code)
    print(response.text)
    print("=====================================")

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Clover error {response.status_code}: {response.text}",
        )

    try:
        checkout = response.json()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Clover returned non-JSON response: "
                f"{response.status_code} {response.text}"
            ),
        )

    lead.status = "started_checkout"

    checkout_id = (
        checkout.get("id")
        or checkout.get("checkoutSessionId")
    )

    lead.clover_checkout_id = checkout_id
    lead.clover_order_id = checkout_id

    db.commit()
    db.refresh(lead)

    checkout_url = (
        checkout.get("href")
        or checkout.get("url")
        or checkout.get("checkoutUrl")
        or checkout.get("checkout_url")
        or checkout.get("paymentLink")
    )

    print("Checkout URL:", checkout_url)
    print("Full Clover Response:", checkout)

    if not checkout_url:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Clover did not return a checkout URL",
                "clover_response": checkout,
            },
        )

    return {
        "success": True,
        "lead_id": lead.id,
        "checkout_id": checkout_id,
        "checkout_url": checkout_url,
    }


def categorize_clover_product(name):
    if not name:
        return "other"

    product_name = name.strip().lower()

    event_keywords = [
        "ticket",
        "general admission",
        "ringside",
        "table seat",
        "admission",
        "fight night",
        "event",
        "kids under",
    ]

    membership_keywords = [
        "membership",
        "month to month",
        "monthly",
        "3 month",
        "3-month",
        "three month",
        "annual",
        "yearly",
        "unlimited boxing",
        "youth boxing",
        "adult boxing",
        "family membership",
    ]

    if any(keyword in product_name for keyword in event_keywords):
        return "event_ticket"

    if any(keyword in product_name for keyword in membership_keywords):
        return "membership"

    return "other"
@app.post("/api/clover/sync-products")
def sync_clover_products(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(status_code=500, detail="Clover credentials missing")

    base_url = "https://api.clover.com" if clover_env == "production" else "https://apisandbox.dev.clover.com"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{base_url}/v3/merchants/{merchant_id}/items",
        headers=headers,
        timeout=20,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Clover product sync error {response.status_code}: {response.text}"
        )

    data = response.json()
    items = data.get("elements", [])

    synced = 0

    for item in items:
        name = item.get("name")
        price_cents = item.get("price", 0)
        category = categorize_clover_product(name)

        if not name:
            continue

        existing = db.query(MembershipProduct).filter(
            MembershipProduct.name == name
        ).first()

        is_membership = category == "membership"

        if existing:
            existing.price = price_cents / 100
            existing.active = True
            existing.category = category
            existing.is_membership = is_membership
        else:
            product = MembershipProduct(
                name=name,
                price=price_cents / 100,
                active=True,
                category=category,
                is_membership=is_membership,
            )
            db.add(product)

        synced += 1

    db.commit()

    return {
        "message": "Clover products synced",
        "synced": synced,
    }
def generate_member_number(db: Session):
    count = db.query(Member).count() + 1
    return f"TNG-{count:06d}"

def generate_digital_member_id():
    return f"TNG-{uuid.uuid4().hex[:8].upper()}"

def generate_barcode(member_number: str):
    return member_number.replace("-", "")

def generate_qr_code(member_number: str):
    return f"member:{member_number}"

def sync_clover_customer_to_marketing(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
):
    normalized_email = normalize_marketing_email(email)
    normalized_phone = normalize_marketing_phone(phone)

    existing = find_marketing_contact(
        db,
        normalized_email,
        phone,
        first_name,
        last_name,
    )

    if existing:
        if first_name:
            existing.first_name = first_name

        if last_name:
            existing.last_name = last_name

        if normalized_email:
            existing.email = normalized_email

        if phone:
            existing.phone = phone

        existing.tags = merge_marketing_tags(
            existing.tags,
            [
                "Clover Customer",
            ],
        )

        existing.active = True
        existing.updated_at = datetime.utcnow()

        return "updated"

    if not normalized_email and not normalized_phone:
        return "skipped"

    contact = MarketingContact(
        first_name=first_name or "",
        last_name=last_name or "",
        email=normalized_email or None,
        phone=phone or None,
        tags=merge_marketing_tags(
            "",
            [
                "Clover Customer",
            ],
        ),
        source="Clover",
        email_opt_in=False,
        sms_opt_in=False,
        email_unsubscribed=False,
        sms_unsubscribed=False,
        active=True,
    )

    db.add(contact)

    return "created"

@app.post("/api/clover/sync-customers")
def sync_clover_customers(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(
            status_code=500,
            detail="Clover credentials missing",
        )

    base_url = (
        "https://api.clover.com"
        if clover_env == "production"
        else "https://apisandbox.dev.clover.com"
    )

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        (
            f"{base_url}/v3/merchants/{merchant_id}/customers"
            "?expand=emailAddresses,phoneNumbers"
            "&limit=1000"
        ),
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Clover customer sync error "
                f"{response.status_code}: {response.text}"
            ),
        )

    customers = response.json().get("elements", [])

    synced = 0
    updated = 0
    skipped = 0

    marketing_created = 0
    marketing_updated = 0
    marketing_skipped = 0

    for customer in customers:
        clover_customer_id = customer.get("id")

        first_name = (
            customer.get("firstName") or ""
        ).strip()

        last_name = (
            customer.get("lastName") or ""
        ).strip()

        email = ""
        phone = ""

        emails = (
            customer.get("emailAddresses", {})
            .get("elements", [])
        )

        if emails:
            email = (
                emails[0].get("emailAddress") or ""
            ).strip().lower()

        phones = (
            customer.get("phoneNumbers", {})
            .get("elements", [])
        )

        if phones:
            phone = (
                phones[0].get("phoneNumber") or ""
            ).strip()

        if (
            not first_name
            and not last_name
            and not email
            and not phone
        ):
            skipped += 1
            marketing_skipped += 1
            continue

        existing = None

        if clover_customer_id:
            existing = (
                db.query(Member)
                .filter(
                    Member.clover_customer_id
                    == clover_customer_id
                )
                .first()
            )

        if not existing and email:
            existing = (
                db.query(Member)
                .filter(
                    func.lower(Member.email)
                    == email.lower()
                )
                .first()
            )

        if not existing and phone:
            existing = (
                db.query(Member)
                .filter(Member.phone == phone)
                .first()
            )

        if (
            not existing
            and first_name
            and last_name
        ):
            existing = (
                db.query(Member)
                .filter(
                    func.lower(Member.first_name)
                    == first_name.lower(),
                    func.lower(Member.last_name)
                    == last_name.lower(),
                )
                .first()
            )

        if existing:
            if clover_customer_id:
                existing.clover_customer_id = (
                    clover_customer_id
                )

            if first_name:
                existing.first_name = first_name

            if last_name:
                existing.last_name = last_name

            if email:
                existing.email = email

            if phone:
                existing.phone = phone

            if not existing.member_number:
                existing.member_number = (
                    f"TNG-{existing.id:06d}"
                )

            if not existing.digital_member_id:
                existing.digital_member_id = (
                    generate_digital_member_id()
                )

            if not existing.barcode:
                existing.barcode = generate_barcode(
                    existing.member_number
                )

            if not existing.qr_code:
                existing.qr_code = generate_qr_code(
                    existing.member_number
                )

            marketing_result = (
                sync_clover_customer_to_marketing(
                    db,
                    first_name,
                    last_name,
                    email,
                    phone,
                )
            )

            if marketing_result == "created":
                marketing_created += 1
            elif marketing_result == "updated":
                marketing_updated += 1
            else:
                marketing_skipped += 1

            updated += 1
            continue

        member = Member(
            first_name=first_name or "Clover",
            last_name=last_name or "Customer",
            email=email,
            phone=phone,
            status="customer",
            membership_status="not_applicable",
            clover_customer_id=clover_customer_id,
            membership_type="Clover Customer",
            member_type="CUSTOMER",
            waiver_signed=False,
        )

        db.add(member)
        db.flush()

        member.member_number = (
            f"TNG-{member.id:06d}"
        )

        member.digital_member_id = (
            generate_digital_member_id()
        )

        member.barcode = generate_barcode(
            member.member_number
        )

        member.qr_code = generate_qr_code(
            member.member_number
        )

        marketing_result = (
            sync_clover_customer_to_marketing(
                db,
                first_name,
                last_name,
                email,
                phone,
            )
        )

        if marketing_result == "created":
            marketing_created += 1
        elif marketing_result == "updated":
            marketing_updated += 1
        else:
            marketing_skipped += 1

        synced += 1

    db.commit()

    return {
        "message": "Clover customers synced",
        "synced": synced,
        "updated": updated,
        "skipped": skipped,
        "marketing": {
            "created": marketing_created,
            "updated": marketing_updated,
            "skipped": marketing_skipped,
        },
    }

@app.post("/api/members/activate-prospects")
def activate_prospects(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    prospects = (
        db.query(Member)
        .filter(Member.membership_type == "Prospect")
        .all()
    )

    for member in prospects:
        member.status = "active"
        member.membership_status = "active"
        member.membership_type = "Active Member"

        if not member.membership_start:
            member.membership_start = datetime.utcnow()

    db.commit()

    return {
        "message": "Prospects changed to active members",
        "updated": len(prospects),
    }
@app.get("/api/users")
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    users = db.query(User).order_by(User.name.asc()).all()

    results = []

    for account in users:
        rep = account.rep_profile

        results.append({
            "id": account.id,
            "name": account.name,
            "email": account.email,
            "role": account.role,
            "active": account.active,
            "sales_rep_id": rep.id if rep else None,
            "phone": rep.phone if rep else "",
            "referral_slug": rep.referral_slug if rep else "",
            "clover_link": rep.clover_link if rep else "",
        })

    return results


@app.post("/api/users")
def create_user_account(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()

    phone = (data.get("phone") or "").strip()
    referral_slug = (data.get("referral_slug") or "").strip().lower()
    clover_link = (data.get("clover_link") or "").strip()

    if not name or not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Name, email, and password are required",
        )

    if role not in ["admin", "staff", "rep"]:
        raise HTTPException(
            status_code=400,
            detail="Role must be admin, staff, or rep",
        )

    existing_user = db.query(User).filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists",
        )

    if role == "rep":
        if not referral_slug:
            raise HTTPException(
                status_code=400,
                detail="Referral slug is required for sales reps",
            )

        existing_slug = db.query(SalesRep).filter(
            func.lower(SalesRep.referral_slug) == referral_slug
        ).first()

        if existing_slug:
            raise HTTPException(
                status_code=400,
                detail="Referral slug already exists",
            )

    account = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        active=True,
    )

    db.add(account)
    db.flush()

    rep = None

    if role == "rep":
        rep = SalesRep(
            user_id=account.id,
            phone=phone,
            referral_slug=referral_slug,
            clover_link=clover_link,
        )

        db.add(rep)

    db.commit()
    db.refresh(account)

    if rep:
        db.refresh(rep)

    return {
        "message": "User account created successfully",
        "user": {
            "id": account.id,
            "name": account.name,
            "email": account.email,
            "role": account.role,
            "active": account.active,
            "sales_rep_id": rep.id if rep else None,
            "referral_slug": rep.referral_slug if rep else "",
        },
    }

@app.post("/api/clover/sync-sales")
def sync_clover_sales(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(status_code=500, detail="Clover credentials missing")

    base_url = "https://api.clover.com" if clover_env == "production" else "https://apisandbox.dev.clover.com"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{base_url}/v3/merchants/{merchant_id}/orders?expand=payments,lineItems,customers&limit=1000",
        headers=headers,
        timeout=30,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Clover sales sync error {response.status_code}: {response.text}"
        )

    orders = response.json().get("elements", [])

    synced = 0
    skipped = 0

    default_rep = db.query(SalesRep).first()
    default_product = db.query(MembershipProduct).first()

    if not default_rep or not default_product:
        raise HTTPException(
            status_code=400,
            detail="Need at least one sales rep and one membership product before syncing sales"
        )

    for order in orders:
        order_id = order.get("id")
        total_cents = order.get("total", 0) or 0

        if not order_id or total_cents <= 0:
            skipped += 1
            continue

        payment_id = ""
        payments = order.get("payments", {}).get("elements", [])
        if payments:
            payment_id = payments[0].get("id") or ""

        existing_sale = db.query(Sale).filter(
            (Sale.clover_order_id == order_id) |
            (Sale.clover_payment_id == payment_id)
        ).first()

        if existing_sale:
            skipped += 1
            continue

        customer_id = ""
        customers = order.get("customers", {}).get("elements", [])
        if customers:
            customer_id = customers[0].get("id") or ""

        member = None

        # Match by Clover Customer ID
        if customer_id:
            member = db.query(Member).filter(
                Member.clover_customer_id == customer_id
            ).first()

        # If not found, try matching by email
        if not member:
            customers = order.get("customers", {}).get("elements", [])
            if customers:
                emails = customers[0].get("emailAddresses", {}).get("elements", [])
                if emails:
                    email = emails[0].get("emailAddress")
                    if email:
                        member = db.query(Member).filter(
                            Member.email == email
                        ).first()

        # If still not found, try matching by phone
        if not member:
            customers = order.get("customers", {}).get("elements", [])
            if customers:
                phones = customers[0].get("phoneNumbers", {}).get("elements", [])
                if phones:
                    phone = phones[0].get("phoneNumber")
                    if phone:
                        member = db.query(Member).filter(
                            Member.phone == phone
                        ).first()

        if not member:
            skipped += 1
            continue

        created_time = order.get("createdTime") or order.get("clientCreatedTime")

        sale_date = datetime.utcnow()
        if created_time:
            try:
                sale_date = datetime.fromtimestamp(int(created_time) / 1000)
            except Exception:
                sale_date = datetime.utcnow()
        product = default_product

        line_items = order.get("lineItems", {}).get("elements", [])
        if line_items:
            clover_item_name = line_items[0].get("name") or ""

            if clover_item_name:
                matched_product = db.query(MembershipProduct).filter(
                    MembershipProduct.name == clover_item_name
                ).first()

                if matched_product:
                    product = matched_product
        is_membership_product = (
            (product.category or "").strip().lower()
            in {
                "membership",
                "monthly_membership",
                "annual_membership",
            }
        )

        sale = Sale(
            member_id=member.id,
            sales_rep_id=default_rep.id,
            product_id=product.id,
            amount=total_cents / 100,
            payment_status="paid",
            transaction_status="paid",
            clover_order_id=order_id,
            clover_payment_id=payment_id,
            payment_method="clover",
            sale_date=sale_date,
            sale_type=(
                "membership"
                if is_membership_product
                else (product.category or "other")
            ),
        )

        db.add(sale)

        if is_membership_product:
            if not member.membership_start:
                member.membership_start = sale_date

            apply_membership(
    member,
    product,
    purchase_date=sale_date,
)
            member.last_payment_date = sale_date

        synced += 1

    db.commit()

    members_with_sales = (
        db.query(Member)
        .join(Sale)
        .distinct()
        .all()
    )

    for member in members_with_sales:
        recalculate_member_from_payments(member, db)

    db.commit()

    return {
        "message": "Clover sales synced",
        "synced": synced,
        "skipped": skipped,
    }

@app.post("/api/clover/sync-all")
def sync_all_clover(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    products = sync_clover_products(db, user)
    customers = sync_clover_customers(db, user)
    sales = sync_clover_sales(db, user)

    return {
        "message": "Clover sync complete",
        "products": products,
        "customers": customers,
        "sales": sales,
    }

@app.post("/api/clover/reset-imported-sales")
def reset_imported_clover_sales(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)

    sales = db.query(Sale).filter(
        Sale.payment_method == "clover",
        Sale.clover_order_id != None
    ).all()

    deleted = len(sales)

    for sale in sales:
        db.delete(sale)

    db.commit()

    return {
        "message": "Imported Clover sales cleared",
        "deleted": deleted,
    }

@app.get("/api/members/{member_id}/payments")
def member_payments(member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    member = db.query(Member).filter(Member.id == member_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    sales = (
        db.query(Sale)
        .filter(Sale.member_id == member_id)
        .order_by(Sale.sale_date.desc())
        .all()
    )

    return {
        "member_id": member.id,
        "member_name": f"{member.first_name} {member.last_name}",
        "total_payments": len(sales),
        "lifetime_value": sum(s.amount or 0 for s in sales),
        "payments": [
            {
                "id": s.id,
                "amount": s.amount,
                "payment_status": s.payment_status,
                "transaction_status": s.transaction_status,
                "payment_method": s.payment_method,
                "clover_order_id": s.clover_order_id,
                "clover_payment_id": s.clover_payment_id,
                "sale_date": s.sale_date.isoformat() if s.sale_date else None,
                "membership": s.product.name if s.product else "",
            }
            for s in sales
        ],
    }

@app.post("/api/clover/webhook")
async def clover_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    print("========== CLOVER WEBHOOK ==========")
    print(payload)
    print("====================================")

    event_type = payload.get("type") or payload.get("eventType") or ""
    payment_id = payload.get("paymentId") or payload.get("id")
    checkout_id = payload.get("checkoutId") or payload.get("checkoutSessionId") or payload.get("orderId")
    hosted_checkout_id = payload.get("data") or payload.get("Data") or checkout_id
    webhook_status = str(payload.get("status") or payload.get("Status") or "").upper()
    event_type_upper = str(event_type).upper()

    if event_type_upper != "PAYMENT":
        return {
            "received": True,
            "message": f"Ignored non-payment event: {event_type}",
        }

    if webhook_status in ["DECLINED", "FAILED"]:
        matching_checkout_id = str(hosted_checkout_id or checkout_id or "")

        if matching_checkout_id:
            failed_lead = db.query(Lead).filter(
                (Lead.clover_checkout_id == matching_checkout_id)
                | (Lead.clover_order_id == matching_checkout_id)
            ).first()

            if failed_lead:
                failed_lead.status = "payment_failed"
                db.commit()

        return {
            "received": True,
            "message": "Payment was not approved",
            "status": webhook_status,
        }

    if webhook_status != "APPROVED":
        return {
            "received": True,
            "message": f"Ignored unsupported payment status: {webhook_status}",
        }

    merchandise_checkout = None
    if hosted_checkout_id:
        merchandise_checkout = db.query(MerchandiseCheckout).filter(
            MerchandiseCheckout.clover_checkout_id == str(hosted_checkout_id)
        ).first()

    if merchandise_checkout:
        if webhook_status == "APPROVED" or str(event_type).upper() == "PAYMENT":
            finalize_merchandise_checkout(
                merchandise_checkout,
                payment_id or "",
                payload.get("orderId") or "",
                db,
            )
            return {
                "received": True,
                "message": "Merchandise payment recorded",
                "checkout_id": merchandise_checkout.id,
            }

        if webhook_status in ["DECLINED", "FAILED"]:
            merchandise_checkout.status = "failed"
            db.commit()
            return {"received": True, "message": "Merchandise payment failed"}

    lead = None

    matching_checkout_id = str(hosted_checkout_id or checkout_id or "")

    if matching_checkout_id:
        lead = db.query(Lead).filter(
            (Lead.clover_checkout_id == matching_checkout_id)
            | (Lead.clover_order_id == matching_checkout_id)
        ).first()



    if not lead:
        return {
            "received": True,
            "message": "No matching lead found",
            "checkout_id": matching_checkout_id,
        }

    product = db.query(MembershipProduct).filter(MembershipProduct.id == lead.product_id).first()

    # Prevent duplicate members by matching email first, then phone.
    normalized_email = (lead.email or "").strip().lower()
    normalized_phone = "".join(
        character for character in (lead.phone or "") if character.isdigit()
    )

    existing_member = None

    if normalized_email:
        existing_member = (
            db.query(Member)
            .filter(Member.email == normalized_email)
            .first()
        )

    if not existing_member and normalized_phone:
        possible_phone_matches = (
            db.query(Member)
            .filter(Member.phone.isnot(None))
            .all()
        )

        existing_member = next(
            (
                possible_member
                for possible_member in possible_phone_matches
                if "".join(
                    character
                    for character in (possible_member.phone or "")
                    if character.isdigit()
                ) == normalized_phone
            ),
            None,
        )

    if existing_member:
        member = existing_member

        # Update the existing member with the newest registration details.
        member.first_name = lead.first_name or member.first_name
        member.last_name = lead.last_name or member.last_name
        member.email = normalized_email or member.email
        member.phone = lead.phone or member.phone

        member.address = lead.address or member.address
        member.city = lead.city or member.city
        member.state = lead.state or member.state
        member.zip_code = lead.zip_code or member.zip_code

        member.status = "active"
        member.membership_status = "active"
        member.membership_type = (
            product.name
            if product
            else member.membership_type or "Membership"
        )

        product_name = (product.name if product else "").lower()
        start_date = datetime.utcnow()


        if product:
            apply_membership(
                member=member,
                product=product,
                purchase_date=datetime.utcnow(),
            )

        member = Member(
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=normalized_email or lead.email,
            phone=lead.phone,

            address=lead.address,
            city=lead.city,
            state=lead.state,
            zip_code=lead.zip_code,

            status="active",
            membership_status="active",
            membership_start=start_date,
            membership_end=membership_end,
            membership_type=product.name if product else "Membership",
            waiver_signed=False,
        )

        db.add(member)
        db.flush()

    # Create missing membership credentials for new or existing members.
    if not member.member_number:
        member.member_number = f"TNG-{member.id:06d}"

    if not member.digital_member_id:
        member.digital_member_id = generate_digital_member_id()

    if not member.barcode:
        member.barcode = generate_barcode(member.member_number)

    if not member.qr_code:
        member.qr_code = generate_qr_code(member.member_number)

    db.commit()
    db.refresh(member)

    existing_sale = db.query(Sale).filter(
        Sale.clover_checkout_id == lead.clover_checkout_id
    ).first()

    if not existing_sale and lead.sales_rep_id and product:
        sale = Sale(
            member_id=member.id,
            sales_rep_id=lead.sales_rep_id,
            product_id=product.id,
            amount=product.price,
            payment_status="paid",
            transaction_status="paid",
            clover_checkout_id=lead.clover_checkout_id,
            clover_order_id=lead.clover_order_id or "",
            clover_payment_id=payment_id or "",
            payment_method="clover",
        )
        db.add(sale)

    lead.status = "converted"
    lead.clover_payment_id = payment_id
    lead.paid_at = datetime.utcnow()
    lead.converted_at = datetime.utcnow()

    db.commit()

    return {
        "received": True,
        "message": "Lead converted to member",
        "member_id": member.id,
        "member_number": member.member_number,
    }





@app.post("/api/checkin")
def checkin(data: dict, db: Session = Depends(get_db)):
    code = data.get("code", "").replace("-", "").upper()

    member = db.query(Member).filter(
        (Member.barcode == code) |
        (Member.member_number == code) |
        (Member.qr_code == code)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    attendance = Attendance(
        member_id=member.id,
        method="barcode",
        location="Front Desk"
    )

    db.add(attendance)

    member.last_checkin = datetime.utcnow()
    member.checkins = (member.checkins or 0) + 1
    member.total_checkins = (member.total_checkins or 0) + 1

    db.commit()

    return {
        "success": True,
        "member": {
            "id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "member_number": member.member_number,
            "membership": member.membership_type,
            "status": member.membership_status,
            "last_checkin": member.last_checkin,
            "total_checkins": member.total_checkins,
        }
    }
@app.get("/api/members/{member_id}/attendance")
def member_attendance(member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    member = db.query(Member).filter(Member.id == member_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    rows = (
        db.query(Attendance)
        .filter(Attendance.member_id == member_id)
        .order_by(Attendance.checkin_time.desc())
        .limit(50)
        .all()
    )

    return {
        "member_id": member.id,
        "member_name": f"{member.first_name} {member.last_name}",
        "total_checkins": member.total_checkins or 0,
        "last_checkin": member.last_checkin.isoformat() if member.last_checkin else None,
        "attendance": [
            {
                "id": a.id,
                "checkin_time": a.checkin_time.isoformat() if a.checkin_time else None,
                "checkout_time": a.checkout_time.isoformat() if a.checkout_time else None,
                "method": a.method,
                "location": a.location,
            }
            for a in rows
        ],
    }




@app.get("/api/clover/settings")
def clover_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    settings = db.query(CloverSetting).first()
    return settings or {"merchant_id": "", "environment": "sandbox", "webhook_secret": ""}





@app.get("/api/duplicates/members")
def find_duplicate_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    members = db.query(Member).all()
    results = []

    def member_summary(m):
        payments = db.query(Sale).filter(Sale.member_id == m.id).all()
        payment_count = len(payments)
        lifetime_value = sum(s.amount or 0 for s in payments)
        attendance_count = db.query(Attendance).filter(
            Attendance.member_id == m.id
        ).count()

        score = 0
        if m.clover_customer_id:
            score += 100
        if payment_count:
            score += payment_count * 10
        if attendance_count:
            score += min(attendance_count, 50)
        if m.photo_url:
            score += 15
        if m.membership_status == "active":
            score += 20
        if m.email:
            score += 5
        if m.phone:
            score += 5

        return {
            "id": m.id,
            "name": f"{m.first_name or ''} {m.last_name or ''}".strip(),
            "email": m.email,
            "phone": m.phone,
            "member_number": m.member_number,
            "membership_type": m.membership_type,
            "membership_status": m.membership_status,

            "membership_start": m.membership_start.isoformat() if m.membership_start else None,
            "membership_end": m.membership_end.isoformat() if m.membership_end else None,
            "last_payment_date": m.last_payment_date.isoformat() if m.last_payment_date else None,

            "clover_customer_id": m.clover_customer_id,
            "photo_url": m.photo_url,
            "payment_count": payment_count,
            "lifetime_value": lifetime_value,
            "attendance_count": attendance_count,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "score": score,
        }

    for i, a in enumerate(members):
        for b in members[i + 1:]:
            reasons = []
            confidence = 0

            if a.email and b.email and a.email.lower() == b.email.lower():
                reasons.append("Same email")
                confidence = max(confidence, 100)

            if a.phone and b.phone and a.phone == b.phone:
                reasons.append("Same phone")
                confidence = max(confidence, 100)

            if (
                a.clover_customer_id
                and b.clover_customer_id
                and a.clover_customer_id == b.clover_customer_id
            ):
                reasons.append("Same Clover Customer ID")
                confidence = max(confidence, 100)

            if (
                a.first_name
                and b.first_name
                and a.last_name
                and b.last_name
                and a.first_name.lower() == b.first_name.lower()
                and a.last_name.lower() == b.last_name.lower()
            ):
                reasons.append("Same first and last name")
                confidence = max(confidence, 90)

            if reasons:
                summary_a = member_summary(a)
                summary_b = member_summary(b)

                if summary_a["score"] >= summary_b["score"]:
                    recommended_keep_id = a.id
                    recommended_merge_id = b.id
                else:
                    recommended_keep_id = b.id
                    recommended_merge_id = a.id

                results.append({
                    "member_a": summary_a,
                    "member_b": summary_b,
                    "reasons": reasons,
                    "confidence": confidence,
                    "recommended_keep_id": recommended_keep_id,
                    "recommended_merge_id": recommended_merge_id,
                })

    return results

@app.post("/api/duplicates/members/merge")
def merge_duplicate_members(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    keep_id = data.get("keep_id")
    merge_id = data.get("merge_id")

    if not keep_id or not merge_id or keep_id == merge_id:
        raise HTTPException(status_code=400, detail="Invalid merge request")

    keep = db.query(Member).filter(Member.id == keep_id).first()
    merge = db.query(Member).filter(Member.id == merge_id).first()

    if not keep or not merge:
        raise HTTPException(status_code=404, detail="Member not found")

    # Move attendance
    db.query(Attendance).filter(
        Attendance.member_id == merge.id
    ).update({"member_id": keep.id})

    # Move sales/payments
    db.query(Sale).filter(
        Sale.member_id == merge.id
    ).update({"member_id": keep.id})

    # Fill missing profile fields
    fields = [
        "email",
        "phone",
        "photo_url",
        "clover_customer_id",
        "membership_type",
        "membership_status",
        "membership_start",
        "membership_end",
        "billing_cycle",
        "monthly_rate",
        "next_billing_date",
        "autopay_enabled",
        "billing_status",
        "last_payment_date",
        "past_due_amount",
        "notes",
    ]

    for field in fields:
        if not getattr(keep, field, None) and getattr(merge, field, None):
            setattr(keep, field, getattr(merge, field))

    keep.total_checkins = (keep.total_checkins or 0) + (merge.total_checkins or 0)
    keep.checkins = (keep.checkins or 0) + (merge.checkins or 0)

    if merge.last_checkin and (
        not keep.last_checkin or merge.last_checkin > keep.last_checkin
    ):
        keep.last_checkin = merge.last_checkin

    db.delete(merge)
    db.commit()
    db.refresh(keep)

    return {
        "message": "Members merged successfully",
        "kept_member_id": keep.id,
        "deleted_member_id": merge_id,
    }

class AIWorkoutRequest(BaseModel):
    module: str
    level: str
    stance: str
    rounds: int = Field(default=6)
    round_time: int = Field(default=180)
    pace_seconds: int = Field(default=10)
@app.post("/api/ai/training-plan")
def generate_ai_training_plan(
    data: AIWorkoutRequest,
    user: User = Depends(current_user),
):
    require_admin(user)

    if not client:
        raise HTTPException(
            status_code=503,
            detail="OpenAI is not configured on the backend.",
        )

    allowed_modules = {
        "Heavy Bag",
        "Shadowboxing",
        "Defense / Reaction",
        "Footwork",
        "Boxing Conditioning",
        "Dynamic Warm-Up",
        "Core",
        "Fight Camp Progressive",
        "Ring IQ",
    }

    allowed_levels = {
        "beginner",
        "intermediate",
        "advanced",
    }

    allowed_stances = {
        "orthodox",
        "southpaw",
    }

    if data.module not in allowed_modules:
        raise HTTPException(
            status_code=400,
            detail="Invalid training module.",
        )

    if data.level not in allowed_levels:
        raise HTTPException(
            status_code=400,
            detail="Invalid training level.",
        )

    if data.stance not in allowed_stances:
        raise HTTPException(
            status_code=400,
            detail="Invalid boxing stance.",
        )

    safe_rounds = max(1, min(int(data.rounds), 20))
    safe_round_time = max(30, min(int(data.round_time), 600))
    safe_pace = max(5, min(int(data.pace_seconds), 60))

    commands_per_round = max(
        3,
        min(
            18,
            safe_round_time // safe_pace,
        ),
    )

    system_prompt = """
You are TNG Coach AI, an expert boxing training and tactical-development
assistant for TNG Boxing.

Create practical boxing workouts that can be spoken aloud while an athlete
is actively training.

The three levels must be clearly different.

BEGINNER:
- One simple decision at a time.
- Basic stance, balance, guard, jab, cross, simple defense and movement.
- Short combinations.
- Direct and easy-to-understand instructions.
- Core exercises must be stable and controlled.

INTERMEDIATE:
- Two-part tactical decisions.
- Pattern recognition, feints, body-head attacks, counters, angles and exits.
- Moderate combinations with defensive responsibility.
- Core exercises should include rotation, anti-extension and lateral control.

ADVANCED:
- Do not merely make combinations longer.
- Use layered tactical decisions.
- Include trap setting, false openings, rhythm changes, opponent tendencies,
  counter-counters, ring position, score awareness and time awareness.
- Require the athlete to recognize a trigger, respond correctly and finish
  in a superior position.
- Core exercises should use advanced anti-rotation, rotational control,
  unilateral stability and boxing-specific movement.

RING IQ:
- State what the opponent is doing.
- State what the athlete should recognize.
- Give the tactical response.
- Finish with the correct exit or ring position.

CORE:
- Change exercises throughout the workout.
- Match exercise difficulty to the selected level.
- Include a short technique cue.
- Prioritize safe trunk control over uncontrolled speed.

FIGHT CAMP PROGRESSIVE:
- Every round must build on the previous round.
- Early rounds establish technique and reads.
- Middle rounds increase tactical pressure.
- Final rounds include fatigue, score, time and opponent adjustments.

Keep every spoken command concise enough to understand during training.
Return JSON only.
"""

    user_prompt = f"""
Create a boxing workout using these settings:

Module: {data.module}
Level: {data.level}
Stance: {data.stance}
Rounds: {safe_rounds}
Round duration: {safe_round_time} seconds
Commands per round: approximately {commands_per_round}

Return exactly this JSON structure:

{{
  "title": "Workout title",
  "module": "{data.module}",
  "level": "{data.level}",
  "stance": "{data.stance}",
  "progression_summary": "Short explanation of the workout progression",
  "rounds": [
    {{
      "round_number": 1,
      "module": "Module used during this round",
      "title": "Round title",
      "objective": "Main objective",
      "commands": [
        {{
          "prompt": "Short spoken training command",
          "coaching_cue": "Short technical coaching reminder",
          "objective": "Purpose of the command",
          "opponent_trigger": "Opponent action or situation, or null",
          "correct_exit": "Correct final position or exit"
        }}
      ]
    }}
  ]
}}

Create exactly {safe_rounds} rounds.
Make the rounds progressive rather than random.
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv(
                "OPENAI_TRAINER_MODEL",
                "gpt-4.1-mini",
            ),
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format={
                "type": "json_object",
            },
        )

        raw_content = response.choices[0].message.content

        if not raw_content:
            raise ValueError("OpenAI returned an empty response.")

        workout = json.loads(raw_content)

        generated_rounds = workout.get("rounds")

        if not isinstance(generated_rounds, list):
            raise ValueError(
                "OpenAI response did not include a valid rounds list."
            )

        if len(generated_rounds) != safe_rounds:
            raise ValueError(
                "OpenAI returned the wrong number of rounds."
            )

        return workout

    except json.JSONDecodeError as error:
        logger.exception(
            "AI Trainer returned invalid JSON: %s",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an invalid workout format.",
        )

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "AI Trainer generation failed: %s",
            error,
        )

        raise HTTPException(
            status_code=502,
            detail="The AI workout could not be generated.",
        )



LIVE_AI_SESSION = {
    "active": False,
    "phase": "Ready",
    "round": 0,
    "total_rounds": 0,
    "time_left": 0,
    "module": "TNG Coach AI",
    "prompt": "Waiting for coach to start session",
    "sub_prompt": "Open this screen on every TV in the gym.",
    "updated_at": datetime.utcnow().isoformat(),
}


@app.get("/api/ai/live-session")
def get_live_ai_session():
    return LIVE_AI_SESSION


@app.post("/api/ai/live-session")
def update_live_ai_session(
    data: dict,
    user: User = Depends(current_user),
):
    require_admin(user)

    LIVE_AI_SESSION.update({
        "active": data.get("active", LIVE_AI_SESSION["active"]),
        "phase": data.get("phase", LIVE_AI_SESSION["phase"]),
        "round": data.get("round", LIVE_AI_SESSION["round"]),
        "total_rounds": data.get("total_rounds", LIVE_AI_SESSION["total_rounds"]),
        "time_left": data.get("time_left", LIVE_AI_SESSION["time_left"]),
        "module": data.get("module", LIVE_AI_SESSION["module"]),
        "prompt": data.get("prompt", LIVE_AI_SESSION["prompt"]),
        "sub_prompt": data.get("sub_prompt", LIVE_AI_SESSION["sub_prompt"]),
        "updated_at": datetime.utcnow().isoformat(),
    })

    return LIVE_AI_SESSION

@app.delete("/api/members/{member_id}")
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = db.query(Member).filter(Member.id == member_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Delete attendance
    db.query(Attendance).filter(
        Attendance.member_id == member.id
    ).delete()

    # Delete sales
    db.query(Sale).filter(
        Sale.member_id == member.id
    ).delete()

    # Delete photo
    if member.photo_url:
        try:
            path = member.photo_url.lstrip("/")
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # Delete member
    db.delete(member)
    db.commit()

    return {
        "message": "Member deleted successfully"
    }
def normalize_marketing_email(value):
    return (value or "").strip().lower()


def normalize_marketing_phone(value):
    return "".join(
        character
        for character in (value or "")
        if character.isdigit()
    )


def merge_marketing_tags(existing_tags, new_tags):
    combined = []

    for tag in (existing_tags or "").split(","):
        clean_tag = tag.strip()

        if clean_tag and clean_tag not in combined:
            combined.append(clean_tag)

    for tag in new_tags:
        clean_tag = (tag or "").strip()

        if clean_tag and clean_tag not in combined:
            combined.append(clean_tag)

    return ",".join(combined)

def find_marketing_contact(
    db: Session,
    email: str,
    phone: str,
    first_name: str = "",
    last_name: str = "",
):
    normalized_email = normalize_marketing_email(email)
    normalized_phone = normalize_marketing_phone(phone)

    if normalized_email:
        existing = (
            db.query(MarketingContact)
            .filter(
                func.lower(MarketingContact.email)
                == normalized_email
            )
            .first()
        )

        if existing:
            return existing

    if normalized_phone:
        contacts_with_phone = (
            db.query(MarketingContact)
            .filter(MarketingContact.phone != None)
            .all()
        )

        for contact in contacts_with_phone:
            if (
                normalize_marketing_phone(contact.phone)
                == normalized_phone
            ):
                return contact

    clean_first_name = (
        first_name or ""
    ).strip().lower()

    clean_last_name = (
        last_name or ""
    ).strip().lower()

    if clean_first_name and clean_last_name:
        existing = (
            db.query(MarketingContact)
            .filter(
                func.lower(MarketingContact.first_name)
                == clean_first_name,
                func.lower(MarketingContact.last_name)
                == clean_last_name,
            )
            .first()
        )

        if existing:
            return existing

    return None

@app.post("/api/marketing/sync-audiences")
def sync_marketing_audiences(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    created = 0
    updated = 0
    skipped = 0

    member_created = 0
    member_updated = 0
    lead_created = 0
    lead_updated = 0

    members = db.query(Member).all()

    for member in members:
        email = normalize_marketing_email(member.email)
        phone = (member.phone or "").strip()

        if not email and not normalize_marketing_phone(phone):
            skipped += 1
            continue

        member_status = (
            member.membership_status or ""
        ).strip().lower()

        if member_status == "active":
            audience_tag = "Active Member"
        elif member_status in {
            "inactive",
            "expired",
            "cancelled",
            "canceled",
        }:
            audience_tag = "Expired Member"
        else:
            audience_tag = "Member"

        existing = find_marketing_contact(
            db,
            email,
            phone,
        )

        if existing:
            if member.first_name:
                existing.first_name = member.first_name

            if member.last_name:
                existing.last_name = member.last_name

            if email:
                existing.email = email

            if phone:
                existing.phone = phone

            existing.tags = merge_marketing_tags(
                existing.tags,
                [
                    "Member",
                    audience_tag,
                ],
            )

            existing.source = (
                existing.source or "TNG OS"
            )

            existing.active = True
            existing.updated_at = datetime.utcnow()

            updated += 1
            member_updated += 1
        else:
            contact = MarketingContact(
                first_name=member.first_name or "",
                last_name=member.last_name or "",
                email=email or None,
                phone=phone or None,
                tags=merge_marketing_tags(
                    "",
                    [
                        "Member",
                        audience_tag,
                    ],
                ),
                source="TNG Members",
                email_opt_in=False,
                sms_opt_in=False,
                email_unsubscribed=False,
                sms_unsubscribed=False,
                active=True,
            )

            db.add(contact)

            created += 1
            member_created += 1

    leads = db.query(Lead).all()

    for lead in leads:
        email = normalize_marketing_email(lead.email)
        phone = (lead.phone or "").strip()

        if not email and not normalize_marketing_phone(phone):
            skipped += 1
            continue

        lead_status = (
            lead.status or "new"
        ).strip().lower()

        status_tag = (
            f"Lead - {lead_status.title()}"
        )

        existing = find_marketing_contact(
            db,
            email,
            phone,
        )

        if existing:
            if lead.first_name and not existing.first_name:
                existing.first_name = lead.first_name

            if lead.last_name and not existing.last_name:
                existing.last_name = lead.last_name

            if email and not existing.email:
                existing.email = email

            if phone and not existing.phone:
                existing.phone = phone

            existing.tags = merge_marketing_tags(
                existing.tags,
                [
                    "Lead",
                    status_tag,
                ],
            )

            existing.active = True
            existing.updated_at = datetime.utcnow()

            updated += 1
            lead_updated += 1
        else:
            contact = MarketingContact(
                first_name=lead.first_name or "",
                last_name=lead.last_name or "",
                email=email or None,
                phone=phone or None,
                tags=merge_marketing_tags(
                    "",
                    [
                        "Lead",
                        status_tag,
                    ],
                ),
                source="TNG Leads",
                email_opt_in=False,
                sms_opt_in=False,
                email_unsubscribed=False,
                sms_unsubscribed=False,
                active=True,
            )

            db.add(contact)

            created += 1
            lead_created += 1

    db.commit()

    total_contacts = (
        db.query(MarketingContact)
        .filter(MarketingContact.active == True)
        .count()
    )

    return {
        "message": "Marketing audiences synced.",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "members": {
            "created": member_created,
            "updated": member_updated,
        },
        "leads": {
            "created": lead_created,
            "updated": lead_updated,
        },
        "total_marketing_contacts": total_contacts,
    }

@app.post("/api/marketing/contacts/import")
async def import_marketing_contacts(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    filename = (file.filename or "").lower()
    contents = await file.read()

    try:
        if filename.endswith(".csv"):
            dataframe = pd.read_csv(io.BytesIO(contents), dtype=str).fillna("")
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            dataframe = pd.read_excel(io.BytesIO(contents), dtype=str).fillna("")
        else:
            raise HTTPException(
                status_code=400,
                detail="Upload a CSV or Excel file",
            )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read spreadsheet: {error}",
        )

    def clean(value):
        if value is None:
            return ""
        value = str(value).strip()
        if value.lower() == "nan":
            return ""
        return value

    def find_column(possible_names):
        normalized = {
            str(column).strip().lower(): column
            for column in dataframe.columns
        }

        for name in possible_names:
            if name in normalized:
                return normalized[name]

        return None

    first_name_column = find_column([
        "first name",
        "firstname",
        "given name",
        "first_name",
    ])

    last_name_column = find_column([
        "last name",
        "lastname",
        "family name",
        "last_name",
    ])

    full_name_column = find_column([
        "name",
        "full name",
        "display name",
    ])

    email_column = find_column([
        "email",
        "email address",
        "e-mail",
        "email 1 - value",
    ])

    phone_column = find_column([
        "phone",
        "phone number",
        "mobile",
        "mobile phone",
        "phone 1 - value",
    ])

    company_column = find_column([
        "company",
        "organization",
        "organization 1 - name",
        "business",
    ])

    address_column = find_column([
        "address",
        "street",
        "street address",
    ])

    city_column = find_column(["city"])
    state_column = find_column(["state", "region"])
    postal_column = find_column([
        "postal code",
        "zip",
        "zip code",
    ])

    source_column = find_column(["source", "source file"])
    tags_column = find_column(["tags", "tag", "labels"])

    imported = 0
    updated = 0
    skipped = 0

    for _, row in dataframe.iterrows():
        first_name = clean(row.get(first_name_column, "")) if first_name_column else ""
        last_name = clean(row.get(last_name_column, "")) if last_name_column else ""
        full_name = clean(row.get(full_name_column, "")) if full_name_column else ""

        if not first_name and not last_name and full_name:
            name_parts = full_name.split(maxsplit=1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

        email = clean(row.get(email_column, "")).lower() if email_column else ""
        phone = clean(row.get(phone_column, "")) if phone_column else ""

        company = clean(row.get(company_column, "")) if company_column else ""
        address = clean(row.get(address_column, "")) if address_column else ""
        city = clean(row.get(city_column, "")) if city_column else ""
        state = clean(row.get(state_column, "")) if state_column else ""
        postal_code = clean(row.get(postal_column, "")) if postal_column else ""
        tags = clean(row.get(tags_column, "")) if tags_column else ""
        source = clean(row.get(source_column, "")) if source_column else filename

        if not first_name and not last_name and not email and not phone:
            skipped += 1
            continue

        existing = None

        if email:
            existing = (
                db.query(MarketingContact)
                .filter(func.lower(MarketingContact.email) == email)
                .first()
            )

        if not existing and phone:
            existing = (
                db.query(MarketingContact)
                .filter(MarketingContact.phone == phone)
                .first()
            )

        if existing:
            if first_name and not existing.first_name:
                existing.first_name = first_name
            if last_name and not existing.last_name:
                existing.last_name = last_name
            if email and not existing.email:
                existing.email = email
            if phone and not existing.phone:
                existing.phone = phone
            if company and not existing.company:
                existing.company = company
            if address and not existing.address:
                existing.address = address
            if city and not existing.city:
                existing.city = city
            if state and not existing.state:
                existing.state = state
            if postal_code and not existing.postal_code:
                existing.postal_code = postal_code
            if tags and not existing.tags:
                existing.tags = tags

            existing.updated_at = datetime.utcnow()
            updated += 1
            continue

        contact = MarketingContact(
            first_name=first_name,
            last_name=last_name,
            email=email or None,
            phone=phone or None,
            company=company or None,
            address=address or None,
            city=city or None,
            state=state or None,
            postal_code=postal_code or None,
            tags=tags,
            source=source or filename,
            email_opt_in=False,
            sms_opt_in=False,
            active=True,
        )

        db.add(contact)
        imported += 1

    db.commit()

    return {
        "message": "Contact import complete",
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "total_rows": len(dataframe),
    }
@app.get("/api/marketing/contacts")
def list_marketing_contacts(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    contacts = (
        db.query(MarketingContact)
        .filter(MarketingContact.active == True)
        .order_by(
            MarketingContact.last_name.asc(),
            MarketingContact.first_name.asc(),
        )
        .all()
    )

    results = []

    for contact in contacts:
        tag_list = [
            tag.strip()
            for tag in (contact.tags or "").split(",")
            if tag.strip()
        ]

        results.append({
            "id": contact.id,
            "first_name": contact.first_name or "",
            "last_name": contact.last_name or "",
            "email": contact.email or "",
            "phone": contact.phone or "",
            "company": contact.company or "",
            "address": contact.address or "",
            "city": contact.city or "",
            "state": contact.state or "",
            "postal_code": contact.postal_code or "",
            "tags": tag_list,
            "source": contact.source or "",
            "email_opt_in": bool(contact.email_opt_in),
            "sms_opt_in": bool(contact.sms_opt_in),
            "email_unsubscribed": bool(contact.email_unsubscribed),
            "sms_unsubscribed": bool(contact.sms_unsubscribed),
            "active": bool(contact.active),
            "created_at": (
                contact.created_at.isoformat()
                if contact.created_at
                else None
            ),
            "updated_at": (
                contact.updated_at.isoformat()
                if contact.updated_at
                else None
            ),
        })

    return results
from pydantic import BaseModel

class MarketingPrompt(BaseModel):
    prompt: str
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: str

@app.post("/api/marketing/generate")
def generate_marketing(
    request: MarketingPrompt,
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": """
You are the TNG Boxing Marketing AI.

Return ONLY valid JSON.

{
 "subject":"",
 "email":"",
 "sms":"",
 "social":""
}
                """,
            },
            {
                "role": "user",
                "content": request.prompt,
            },
        ],
        temperature=0.8,
    )

    import json

    return json.loads(
        response.choices[0].message.content
    )

@app.post("/api/marketing/campaigns")
def create_marketing_campaign(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    name = (data.get("name") or "").strip()
    campaign_type = (
        data.get("campaign_type") or ""
    ).strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()
    contact_ids = data.get("contact_ids") or []

    if campaign_type not in [
        "email",
        "sms",
        "social",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Campaign type must be email, sms, or social.",
        )

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Campaign name is required.",
        )

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Campaign message is required.",
        )

    if campaign_type == "email" and not subject:
        raise HTTPException(
            status_code=400,
            detail="Email subject is required.",
        )

    clean_contact_ids = []

    for contact_id in contact_ids:
        try:
            clean_contact_ids.append(int(contact_id))
        except (TypeError, ValueError):
            continue

    campaign = MarketingCampaign(
        name=name,
        campaign_type=campaign_type,
        status="draft",
        subject=subject or None,
        message=message,
        selected_contact_ids=json.dumps(
            clean_contact_ids
        ),
        recipient_count=len(clean_contact_ids),
        created_by_user_id=user.id,
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "message": "Campaign draft saved.",
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "status": campaign.status,
            "subject": campaign.subject,
            "message": campaign.message,
            "recipient_count": campaign.recipient_count,
            "created_at": (
                campaign.created_at.isoformat()
                if campaign.created_at
                else None
            ),
        },
    }

@app.post("/api/marketing/campaigns/{campaign_id}/send")
def send_marketing_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    campaign = (
        db.query(MarketingCampaign)
        .filter(MarketingCampaign.id == campaign_id)
        .first()
    )

    if not campaign:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found.",
        )

    if campaign.campaign_type != "email":
        raise HTTPException(
            status_code=400,
            detail="Only email campaigns can be sent right now.",
        )

    if not resend.api_key:
        raise HTTPException(
            status_code=500,
            detail="RESEND_API_KEY is not configured.",
        )

    try:
        selected_contact_ids = json.loads(
            campaign.selected_contact_ids or "[]"
        )
    except json.JSONDecodeError:
        selected_contact_ids = []

    if not selected_contact_ids:
        raise HTTPException(
            status_code=400,
            detail="No contacts were selected for this campaign.",
        )

    contacts = (
        db.query(MarketingContact)
        .filter(
            MarketingContact.id.in_(selected_contact_ids),
            MarketingContact.email != None,
            MarketingContact.email != "",
        )
        .all()
    )

    if not contacts:
        raise HTTPException(
            status_code=400,
            detail="No selected contacts have valid email addresses.",
        )

    sender_email = os.getenv(
        "RESEND_FROM_EMAIL",
        "TNG Boxing <marketing@tngboxinggym.com>",
    )

    sent_count = 0
    failed_count = 0

    campaign.status = "sending"
    db.commit()

    for contact in contacts:
        contact_name = (
            getattr(contact, "first_name", None)
            or getattr(contact, "name", None)
            or "TNG Member"
        )

        personalized_message = campaign.message.replace(
            "{{first_name}}",
            contact_name,
        )

        html_message = "<br>".join(
            html.escape(personalized_message).splitlines()
        )

        try:
            resend.Emails.send(
                {
                    "from": sender_email,
                    "to": [contact.email],
                    "subject": campaign.subject,
                    "html": html_message,
                }
            )

            sent_count += 1

        except Exception as exc:
            print(
                f"Resend failed for {contact.email}: {exc}"
            )
            failed_count += 1

    campaign.sent_count = sent_count
    campaign.failed_count = failed_count
    campaign.recipient_count = len(contacts)
    campaign.status = (
        "sent"
        if sent_count > 0 and failed_count == 0
        else "partially_sent"
        if sent_count > 0
        else "failed"
    )

    if hasattr(campaign, "sent_at"):
        campaign.sent_at = datetime.utcnow()

    db.commit()
    db.refresh(campaign)

    return {
        "message": "Campaign sending completed.",
        "campaign_id": campaign.id,
        "status": campaign.status,
        "recipient_count": len(contacts),
        "sent_count": sent_count,
        "failed_count": failed_count,
    }

@app.get("/api/marketing/campaigns")
def list_marketing_campaigns(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin_or_staff(user)

    campaigns = (
        db.query(MarketingCampaign)
        .order_by(MarketingCampaign.created_at.desc())
        .all()
    )

    return [
        {
            "id": campaign.id,
            "name": campaign.name,
            "campaign_type": campaign.campaign_type,
            "status": campaign.status,
            "subject": campaign.subject or "",
            "message": campaign.message,
            "recipient_count": campaign.recipient_count or 0,
            "sent_count": campaign.sent_count or 0,
            "delivered_count": (
                campaign.delivered_count or 0
            ),
            "opened_count": campaign.opened_count or 0,
            "clicked_count": campaign.clicked_count or 0,
            "failed_count": campaign.failed_count or 0,
            "scheduled_at": (
                campaign.scheduled_at.isoformat()
                if campaign.scheduled_at
                else None
            ),
            "sent_at": (
                campaign.sent_at.isoformat()
                if campaign.sent_at
                else None
            ),
            "created_at": (
                campaign.created_at.isoformat()
                if campaign.created_at
                else None
            ),
        }
        for campaign in campaigns
    ]

@app.post("/api/email/test")
def send_test_email():
    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv(
        "EMAIL_FROM",
        "TNG Boxing <onboarding@resend.dev>",
    )
    test_email_to = os.getenv("TEST_EMAIL_TO")

    if not resend_api_key:
        raise HTTPException(
            status_code=500,
            detail="RESEND_API_KEY is not configured.",
        )

    if not test_email_to:
        raise HTTPException(
            status_code=500,
            detail="TEST_EMAIL_TO is not configured.",
        )

    try:
        resend.api_key = resend_api_key

        response = resend.Emails.send(
            {
                "from": email_from,
                "to": [test_email_to],
                "subject": "TNG OS Test Email",
                "html": """
                    <div style="font-family: Arial, sans-serif; max-width: 600px;">
                        <h1>TNG OS Email Test</h1>
                        <p>Congratulations!</p>
                        <p>Your TNG OS Resend integration is working.</p>
                        <p><strong>TNG Boxing — Earned Not Given</strong></p>
                    </div>
                """,
            }
        )

        return {
            "success": True,
            "message": "Test email submitted to Resend.",
            "resend_response": response,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Resend failed: {str(exc)}",
        )
@app.get("/test-sms")
def test_sms():
    result = send_sms(
        to_phone="+16512390916",
        message="🎉 TNG OS is now connected to Twilio!"
    )
    return {
        "success": True,
        "result": result
    }
