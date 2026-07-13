from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64, io, qrcode
from openai import OpenAI
import os
import json
import requests
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile, File
import shutil
from sqlalchemy import text
from .database import Base, engine, get_db
from .models import (
    User,
    SalesRep,
    Member,
    MembershipProduct,
    Sale,
    CloverSetting,
    Lead,
    Attendance,
    MerchandiseCheckout,
    SecurityLog,
    MarketingContact,
)
from .schemas import LoginIn, RepCreate, SaleCreate, LeadCreate
from .auth import verify_password, hash_password, create_token, decode_token
from .commission import commission_rate
from sqlalchemy import or_
import sqlite3
import pandas as pd
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
def require_admin_or_staff(user: User):
    if user.role not in ["admin", "staff"]:
        raise HTTPException(status_code=403, detail="Admin or staff access required")
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

def current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    return user


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")


def require_admin_or_staff(user: User):
    if user.role not in ["admin", "staff"]:
        raise HTTPException(
            status_code=403,
            detail="Admin or staff access required",
        )


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

@app.get("/api/products")
def products(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(MembershipProduct).order_by(MembershipProduct.name.asc()).all()
@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    product = db.query(MembershipProduct).filter(
        MembershipProduct.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    allowed_fields = [
        "name",
        "price",
        "active",
        "category",
        "is_membership",
        "renews_monthly",
        "autopay_allowed",
        "default_membership_months",
        "sku",
        "stock_quantity",
        "track_inventory",
    ]

    for field in allowed_fields:
        if field in data:
            setattr(product, field, data[field])
    if "category" in data:
        product.category = (data["category"] or "other").strip().lower()
        product.is_membership = product.category == "membership"

    elif "is_membership" in data:
        product.is_membership = bool(data["is_membership"])

        if product.is_membership:
            product.category = "membership"
        elif product.category == "membership":
            product.category = "other"

    db.commit()
    db.refresh(product)

    return {
        "message": "Product updated",
        "product": {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "active": product.active,
            "category": product.category,
            "is_membership": product.is_membership,
            "renews_monthly": product.renews_monthly,
            "autopay_allowed": product.autopay_allowed,
            "default_membership_months": product.default_membership_months,
            "sku": product.sku,
            "stock_quantity": product.stock_quantity,
            "track_inventory": product.track_inventory,
        },
    }


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
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    today = datetime.utcnow().date()
    now = datetime.utcnow()

    MEMBERSHIP_PRODUCTS = [
        "month",
        "monthly",
        "3 month",
        "annual",
        "year",
        "pre-sale",
        "special",
        "family",
        "vip",
        "non profit",
        "registration",
    ]

    member_filter = or_(
        *[
            Member.membership_type.ilike(f"%{p}%")
            for p in MEMBERSHIP_PRODUCTS
        ]
    )

    total_members = db.query(Member).filter(member_filter).count()

    active_members = (
        db.query(Member)
        .filter(
            member_filter,
            Member.membership_status == "active",
        )
        .count()
    )

    total_leads = db.query(Lead).count()

    today_checkins = (
        db.query(Attendance)
        .filter(func.date(Attendance.checkin_time) == today)
        .count()
    )

    month_sales = (
        db.query(Sale)
        .filter(
            extract("month", Sale.sale_date) == now.month,
            extract("year", Sale.sale_date) == now.year,
        )
        .all()
    )

    revenue_this_month = sum(s.amount or 0 for s in month_sales)

    recent_checkins = (
        db.query(Attendance)
        .order_by(Attendance.checkin_time.desc())
        .limit(10)
        .all()
    )

    recent = []

    for a in recent_checkins:
        member = db.query(Member).filter(Member.id == a.member_id).first()

        recent.append({
            "member": f"{member.first_name} {member.last_name}" if member else "Unknown",
            "time": a.checkin_time.isoformat() if a.checkin_time else None,
            "method": a.method,
        })

    return {
        "total_members": total_members,
        "active_members": active_members,
        "total_leads": total_leads,
        "today_checkins": today_checkins,
        "sales_this_month": len(month_sales),
        "revenue_this_month": revenue_this_month,
        "recent_checkins": recent,
    }

def is_membership_product(product):
    if not product:
        return False

    category = (product.category or "").strip().lower()

    return bool(
        product.is_membership is True
        or category == "membership"
    )
EVENT_TICKET_AMOUNTS = {10.00, 25.00, 50.00}


def is_membership_sale(sale):
    if not sale:
        return False

    if not is_membership_product(sale.product):
        return False

    amount = round(float(sale.amount or 0), 2)

    if amount in EVENT_TICKET_AMOUNTS:
        return False

    return sale.payment_status == "paid"

def apply_membership(member, product):
    membership_start = member.membership_start or datetime.utcnow()
    if not is_membership_product(product):
        return member

    if (
        product
        and (
            "3 month" in product.name.lower()
            or "3-month" in product.name.lower()
            or product.price == 300
        )
    ):
        membership_end = membership_start + relativedelta(months=3)
        billing_cycle = "3_month_prepaid"
        monthly_rate = 0
        next_billing = None
    else:
        membership_end = membership_start + relativedelta(months=1)
        billing_cycle = "monthly"
        monthly_rate = product.price if product else 0
        next_billing = membership_end

    member.membership_type = product.name if product else "Membership"
    member.membership_status = "active"
    member.membership_start = membership_start
    member.membership_end = membership_end
    member.billing_cycle = billing_cycle
    member.monthly_rate = monthly_rate
    member.next_billing_date = next_billing
    member.autopay_enabled = False
    member.billing_status = "active"

    return member
def recalculate_member_from_payments(member, db: Session):
    sales = (
        db.query(Sale)
        .filter(Sale.member_id == member.id)
        .order_by(Sale.sale_date.asc())
        .all()
    )

    membership_sales = [
        sale
        for sale in sales
        if is_membership_sale(sale)
    ]

    if not membership_sales:
        return member

    first_sale = membership_sales[0]
    last_sale = membership_sales[-1]

    member.membership_start = first_sale.sale_date or datetime.utcnow()
    member.membership_end = member.membership_start

    for sale in membership_sales:
        product = sale.product
        sale_date = sale.sale_date or member.membership_end

        if sale_date > member.membership_end:
            member.membership_end = sale_date

        product_name = product.name.lower() if product and product.name else ""

        if (
            "3 month" in product_name
            or "3 months" in product_name
            or "3-month" in product_name
            or (product and product.price == 300)
        ):
            member.membership_end = member.membership_end + relativedelta(months=3)
            member.billing_cycle = "3_month_prepaid"
            member.monthly_rate = 0
            member.next_billing_date = None
            member.autopay_enabled = False
        else:
            member.membership_end = member.membership_end + relativedelta(months=1)
            member.billing_cycle = "monthly"
            member.monthly_rate = product.price if product else 0
            member.next_billing_date = member.membership_end
            member.autopay_enabled = False

        member.membership_type = product.name if product else member.membership_type

    member.last_payment_date = last_sale.sale_date
    member.past_due_amount = 0

    if member.membership_end and member.membership_end < datetime.utcnow():
        member.membership_status = "inactive"
        member.billing_status = "expired"
    else:
        member.membership_status = "active"
        member.billing_status = "active"

    return member
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
        member = apply_membership(member, product)
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

@app.get("/api/join/{slug}")
def join_page_data(slug: str, db: Session = Depends(get_db)):
    rep = db.query(SalesRep).filter(SalesRep.referral_slug == slug).first()
    if not rep:
        raise HTTPException(status_code=404, detail="Rep link not found")
    return {"rep_id": rep.id, "rep_name": rep.user.name, "clover_link": rep.clover_link, "products": db.query(MembershipProduct).filter(MembershipProduct.active == True).all()}

@app.get("/api/members")
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):

    members = (
        db.query(Member)
        .order_by(
            Member.last_name.asc(),
            Member.first_name.asc(),
        )
        .all()
    )

    for member in members:
        recalculate_member_from_payments(member, db)

    db.commit()

    active_members = [
        m for m in members
        if m.membership_status == "active"
    ]

    return [
        {
            "id": member.id,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "email": member.email,
            "phone": member.phone,
            "membership_type": member.membership_type,
            "membership_status": member.membership_status,
            "membership_start": member.membership_start.isoformat() if member.membership_start else None,
            "membership_end": member.membership_end.isoformat() if member.membership_end else None,
            "last_payment_date": member.last_payment_date.isoformat() if member.last_payment_date else None,
            "billing_status": member.billing_status,
            "total_checkins": member.total_checkins or 0,
            "photo_url": member.photo_url,
        }
        for member in active_members
    ]@app.post("/api/products")
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
    api_token = os.getenv("CLOVER_ECOMMERCE_PRIVATE_KEY") or os.getenv("CLOVER_API_TOKEN")
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
        rep = db.query(SalesRep).filter(SalesRep.referral_slug == data.referral_slug).first()

    lead = Lead(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
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
@app.post("/api/clover/create-checkout/{lead_id}")
def create_clover_checkout(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    product = db.query(MembershipProduct).filter(MembershipProduct.id == lead.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Membership product not found")

    merchant_id = os.getenv("CLOVER_MERCHANT_ID")
    api_token = os.getenv("CLOVER_API_TOKEN")
    clover_env = os.getenv("CLOVER_ENV", "production")

    if not merchant_id or not api_token:
        raise HTTPException(status_code=500, detail="Clover credentials missing")

    base_url = "https://api.clover.com" if clover_env == "production" else "https://apisandbox.dev.clover.com"
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
            detail=f"Clover error {response.status_code}: {response.text}"
        )

    try:
        checkout = response.json()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=f"Clover returned non-JSON response: {response.status_code} {response.text}"
        )

    lead.status = "started_checkout"
    lead.clover_checkout_id = checkout.get("id") or checkout.get("checkoutSessionId")
    lead.clover_order_id = checkout.get("id") or checkout.get("checkoutSessionId")
    db.commit()

    checkout_url = checkout.get("href") or checkout.get("url") or checkout.get("checkoutUrl")

    return {
        "lead_id": lead.id,
        "checkout_url": checkout_url,
        "checkout": checkout,
    }
def categorize_clover_product(name):
    if not name:
        return "other"

    n = name.lower()

    event_words = [
        "ga",
        "general admission",
        "kids under",
        "kid",
        "table",
        "table seat",
        "seat",
        "vip",
        "ringside",
        "ticket",
        "admission",
        "fight night",
    ]

    membership_words = [
        "month to month",
        "monthly",
        "membership",
        "3 month",
        "3-month",
        "unlimited boxing",
        "youth boxing",
        "annual",
    ]

    for word in event_words:
        if word in n:
            return "event_ticket"

    for word in membership_words:
        if word in n:
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

        if existing:
            existing.price = price_cents / 100
            existing.active = True
            existing.category = category
            existing.is_membership = (category == "membership")
        else:
            product = MembershipProduct(
                name=name,
                price=price_cents / 100,
                active=True,
                category=category,
                is_membership=(category == "membership"),
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
@app.post("/api/clover/sync-customers")
def sync_clover_customers(db: Session = Depends(get_db), user: User = Depends(current_user)):
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
        f"{base_url}/v3/merchants/{merchant_id}/customers",
        headers=headers,
        timeout=20,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Clover customer sync error {response.status_code}: {response.text}"
        )

    customers = response.json().get("elements", [])

    synced = 0
    skipped = 0
    updated = 0

    for c in customers:
        first_name = c.get("firstName") or ""
        last_name = c.get("lastName") or ""
        email = ""
        phone = ""

        emails = c.get("emailAddresses", {}).get("elements", [])
        if emails:
            email = emails[0].get("emailAddress") or ""

        phones = c.get("phoneNumbers", {}).get("elements", [])
        if phones:
            phone = phones[0].get("phoneNumber") or ""

        if not first_name and not last_name and not email and not phone:
            skipped += 1
            continue

        existing = db.query(Member).filter(
            Member.clover_customer_id == c.get("id")
        ).first()

        if not existing and email:
            existing = db.query(Member).filter(Member.email == email).first()

        if not existing and phone:
            existing = db.query(Member).filter(Member.phone == phone).first()

        if not existing and first_name and last_name:
            existing = db.query(Member).filter(
                func.lower(Member.first_name) == first_name.lower(),
                func.lower(Member.last_name) == last_name.lower(),
            ).first()

        if existing:
            existing.clover_customer_id = c.get("id")
            if email and not existing.email:
                existing.email = email
            if phone and not existing.phone:
                existing.phone = phone
            if first_name:
                existing.first_name = first_name

            if last_name:
                existing.last_name = last_name
            if not existing.member_number:
                existing.member_number = f"TNG-{existing.id:06d}"
                existing.digital_member_id = generate_digital_member_id()
                existing.barcode = generate_barcode(existing.member_number)
                existing.qr_code = generate_qr_code(existing.member_number)
            updated += 1
            continue

        member = Member(
            first_name=first_name or "Clover",
            last_name=last_name or "Customer",
            email=email,
            phone=phone,
            status="active",
            membership_status="inactive",
            clover_customer_id=c.get("id"),
            membership_type="Prospect",
            membership_start=None,
            waiver_signed=False,
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        member.member_number = f"TNG-{member.id:06d}"
        member.digital_member_id = generate_digital_member_id()
        member.barcode = generate_barcode(member.member_number)
        member.qr_code = generate_qr_code(member.member_number)

        db.commit()
        synced += 1

    db.commit()

    return {
        "message": "Clover customers synced",
        "synced": synced,
        "updated": updated,
        "skipped": skipped,
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

            apply_membership(member, product)
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

    if checkout_id:
        lead = db.query(Lead).filter(
            (Lead.clover_checkout_id == checkout_id) |
            (Lead.clover_order_id == checkout_id)
        ).first()

    if not lead:
        lead = db.query(Lead).filter(Lead.status == "started_checkout").order_by(Lead.created_at.desc()).first()

    if not lead:
        return {
            "received": True,
            "message": "No matching lead found"
        }

    product = db.query(MembershipProduct).filter(MembershipProduct.id == lead.product_id).first()

    existing_member = db.query(Member).filter(Member.email == lead.email).first()
    
    if existing_member:
        member = existing_member
    else:
        member = Member(
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            status="active",
            membership_status="active",
            membership_start=datetime.utcnow(),
            membership_type=product.name if product else "Membership",
            waiver_signed=False,
        )

        db.add(member)
        db.commit()
        db.refresh(member)

        member.member_number = f"TNG-{member.id:06d}"
        member.digital_member_id = generate_digital_member_id()
        member.barcode = generate_barcode(member.member_number)
        member.qr_code = generate_qr_code(member.member_number)

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
@app.get("/api/members/{member_id}")
def get_member(member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = db.query(Member).filter(Member.id == member_id).first()

    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    recalculate_member_from_payments(m, db)
    db.commit()
    db.refresh(m)

    return {
        "id": m.id,
        "first_name": m.first_name,
        "last_name": m.last_name,
        "email": m.email,
        "phone": m.phone,
        "status": m.status,
        "member_number": m.member_number,
        "barcode": m.barcode,
        "qr_code": m.qr_code,
        "digital_member_id": m.digital_member_id,
        "membership_type": m.membership_type,
        "membership_status": m.membership_status,
        "membership_start": m.membership_start.isoformat() if m.membership_start else None,
        "membership_end": m.membership_end.isoformat() if m.membership_end else None,

        "billing_cycle": m.billing_cycle,
        "monthly_rate": m.monthly_rate,
        "next_billing_date": m.next_billing_date.isoformat() if m.next_billing_date else None,
        "autopay_enabled": m.autopay_enabled,
        "billing_status": m.billing_status,
        "last_payment_date": m.last_payment_date.isoformat() if m.last_payment_date else None,
        "past_due_amount": m.past_due_amount,
        "clover_customer_id": m.clover_customer_id,
        "last_checkin": m.last_checkin.isoformat() if m.last_checkin else None,
        "total_checkins": m.total_checkins,
        "photo_url": m.photo_url,
        "billing_cycle": m.billing_cycle,
        "monthly_rate": m.monthly_rate,
        "next_billing_date": m.next_billing_date.isoformat() if m.next_billing_date else None,
        "autopay_enabled": m.autopay_enabled,
        "billing_status": m.billing_status,
        "clover_subscription_id": m.clover_subscription_id,
     
        "past_due_amount": m.past_due_amount,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
@app.put("/api/members/{member_id}")
def update_member(member_id: int, data: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = db.query(Member).filter(Member.id == member_id).first()

    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    allowed_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "photo_url",
        "membership_type",
        "membership_status",
        "assigned_coach",
        "emergency_contact",
        "emergency_phone",
        "billing_cycle",
        "monthly_rate",
        "next_billing_date",
        "membership_start",
        "membership_end",
        "autopay_enabled",
        "billing_status",
        "clover_subscription_id",
        "last_payment_date",
        "past_due_amount",
        "notes",
    ]

    date_fields = ["membership_start", "membership_end", "next_billing_date", "last_payment_date"]

    for field in date_fields:
        if field in data and data[field]:
            try:
                data[field] = datetime.fromisoformat(data[field])
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid date format for {field}. Use YYYY-MM-DD.")

    for field in allowed_fields:
        if field in data:
            setattr(m, field, data[field])

    db.commit()
    db.refresh(m)

    return {
        "id": m.id,
        "first_name": m.first_name,
        "last_name": m.last_name,
        "email": m.email,
        "phone": m.phone,
        "photo_url": m.photo_url,
        "member_number": m.member_number,
        "barcode": m.barcode,
        "qr_code": m.qr_code,
        "digital_member_id": m.digital_member_id,
        "membership_type": m.membership_type,
        "membership_status": m.membership_status,
        "membership_start": m.membership_start.isoformat() if m.membership_start else None,
        
        "membership_end": m.membership_end.isoformat() if m.membership_end else None,
        "last_checkin": m.last_checkin.isoformat() if m.last_checkin else None,
        "total_checkins": m.total_checkins,
        "billing_cycle": m.billing_cycle,
        "monthly_rate": m.monthly_rate,
        "next_billing_date": m.next_billing_date.isoformat() if m.next_billing_date else None,
        "autopay_enabled": m.autopay_enabled,
        "billing_status": m.billing_status,
        "clover_subscription_id": m.clover_subscription_id,
        "last_payment_date": m.last_payment_date.isoformat() if m.last_payment_date else None,
        "past_due_amount": m.past_due_amount,
    }
@app.post("/api/members/{member_id}/photo")
def upload_member_photo(
    member_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    m = db.query(Member).filter(Member.id == member_id).first()

    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    ext = file.filename.split(".")[-1].lower()

    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP files are allowed"
        )

    filename = f"{member_id}.{ext}"
    filepath = f"uploads/members/{filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    m.photo_url = f"/uploads/members/{filename}"

    db.commit()
    db.refresh(m)

    return {
        "message": "Photo uploaded successfully",
        "photo_url": m.photo_url,
    }

@app.get("/api/clover/settings")
def clover_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    settings = db.query(CloverSetting).first()
    return settings or {"merchant_id": "", "environment": "sandbox", "webhook_secret": ""}

@app.post("/api/members/{member_id}/renew")
def renew_member(
    member_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = db.query(Member).filter(Member.id == member_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    months = int(data.get("months", 1))

    if months not in [1, 3]:
        raise HTTPException(status_code=400, detail="Renewal must be 1 or 3 months")

    today = datetime.utcnow()
    current_end = member.membership_end if member.membership_end and member.membership_end > today else today

    new_end = current_end + relativedelta(months=months)

    member.membership_start = member.membership_start or today
    member.membership_end = new_end
    member.membership_status = "active"
    member.billing_status = "active"
    member.past_due_amount = 0

    if months == 3:
        member.billing_cycle = "3_month_prepaid"
        member.next_billing_date = None
        member.autopay_enabled = False
    else:
        member.billing_cycle = "monthly"
        member.next_billing_date = new_end

    db.commit()
    db.refresh(member)

    return {
        "message": f"Membership renewed for {months} month(s)",
        "membership_start": member.membership_start.isoformat() if member.membership_start else None,
        "membership_end": member.membership_end.isoformat() if member.membership_end else None,
        "billing_cycle": member.billing_cycle,
        "next_billing_date": member.next_billing_date.isoformat() if member.next_billing_date else None,
        "membership_status": member.membership_status,
        "billing_status": member.billing_status,
    }
@app.post("/api/members/{member_id}/recalculate-membership")
def recalculate_membership(
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    member = db.query(Member).filter(Member.id == member_id).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    sales = (
        db.query(Sale)
        .filter(Sale.member_id == member_id)
        .order_by(Sale.sale_date.asc())
        .all()
    )

    membership_sales = [
        s for s in sales
        if s.product and is_membership_product(s.product)
    ]

    if not membership_sales:
        raise HTTPException(status_code=404, detail="No membership payments found")

    first_sale = membership_sales[0]
    last_sale = membership_sales[-1]

    member.membership_start = first_sale.sale_date or datetime.utcnow()
    member.membership_end = member.membership_start

    for sale in membership_sales:
        product = sale.product
        sale_date = sale.sale_date or member.membership_end

        if sale_date > member.membership_end:
            member.membership_end = sale_date

        if product and (
            "3 month" in product.name.lower()
            or "3 months" in product.name.lower()
            or "3-month" in product.name.lower()
            or product.price == 300
        ):
            member.membership_end = member.membership_end + relativedelta(months=3)
            member.billing_cycle = "3_month_prepaid"
            member.monthly_rate = 0
            member.next_billing_date = None
            member.autopay_enabled = False
        else:
            member.membership_end = member.membership_end + relativedelta(months=1)
            member.billing_cycle = "monthly"
            member.monthly_rate = product.price if product else 0
            member.next_billing_date = member.membership_end

        member.membership_type = product.name if product else member.membership_type

    member.membership_status = "active"
    member.billing_status = "active"
    member.last_payment_date = last_sale.sale_date
    member.past_due_amount = 0

    db.commit()
    db.refresh(member)

    return {
        "message": "Membership recalculated",
        "membership_start": member.membership_start.isoformat() if member.membership_start else None,
        "membership_end": member.membership_end.isoformat() if member.membership_end else None,
        "billing_cycle": member.billing_cycle,
        "next_billing_date": member.next_billing_date.isoformat() if member.next_billing_date else None,
        "last_payment_date": member.last_payment_date.isoformat() if member.last_payment_date else None,
    }

@app.post("/api/members/recalculate-all")
def recalculate_all_memberships(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    require_admin(user)

    members = db.query(Member).all()

    updated = 0
    skipped = 0

    for member in members:
        before_start = member.membership_start
        before_end = member.membership_end

        recalculate_member_from_payments(member, db)

        if member.membership_start != before_start or member.membership_end != before_end:
            updated += 1
        else:
            skipped += 1

    db.commit()

    return {
        "message": "All memberships recalculated",
        "updated": updated,
        "skipped": skipped,
    }

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

    return results@app.post("/api/duplicates/members/merge")
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