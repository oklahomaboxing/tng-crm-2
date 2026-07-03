from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
import base64, io, qrcode
import os
import requests
import uuid
from sqlalchemy import text
from .database import Base, engine, get_db
from .models import User, SalesRep, Member, MembershipProduct, Sale, CloverSetting, Lead
from .schemas import LoginIn, RepCreate, SaleCreate, LeadCreate
from .auth import verify_password, hash_password, create_token, decode_token
from .commission import commission_rate

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

    add_column_if_missing("leads", "clover_checkout_id", "VARCHAR")
    add_column_if_missing("leads", "paid_at", "DATETIME")
    add_column_if_missing("leads", "converted_at", "DATETIME")
    add_column_if_missing("leads", "conversion_source", "VARCHAR")

run_sqlite_migrations()
app = FastAPI(title="TNG CRM 2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://goldfish-app-jq38z.ondigitalocean.app",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def seed_admin():
    db = next(get_db())
    existing = db.query(User).filter(User.email == "admin@tngboxinggym.com").first()
    if not existing:
        admin = User(
            name="TNG Admin",
            email="admin@tngboxinggym.com",
            password_hash=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        db.commit()

seed_admin()
def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

@app.post("/api/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token({"sub": str(user.id), "role": user.role}), "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}

@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    return db.query(MembershipProduct).filter(MembershipProduct.active == True).all()

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
    now = datetime.utcnow()
    q = db.query(Sale).filter(extract('month', Sale.sale_date) == now.month, extract('year', Sale.sale_date) == now.year)
    if user.role == "rep":
        q = q.filter(Sale.sales_rep_id == user.rep_profile.id)
    sales = q.all()
    count = len(sales)
    revenue = sum(s.amount for s in sales)
    rate = commission_rate(count)
    return {"sales_this_month": count, "revenue_this_month": revenue, "commission_rate": rate, "commission_earned": revenue * rate, "next_tier": "10 sales" if count < 10 else "20 sales" if count < 20 else "Max tier"}

@app.post("/api/sales")
def create_sale(data: SaleCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role == "rep" and user.rep_profile.id != data.sales_rep_id:
        raise HTTPException(status_code=403, detail="Reps can only create their own sales")
    product = db.query(MembershipProduct).filter(MembershipProduct.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    member = Member(first_name=data.member_first_name, last_name=data.member_last_name, email=data.member_email, phone=data.member_phone, status="active" if data.payment_status == "paid" else "pending")
    db.add(member); db.flush()
    sale = Sale(member_id=member.id, sales_rep_id=data.sales_rep_id, product_id=product.id, amount=product.price, payment_status=data.payment_status, clover_order_id=data.clover_order_id, clover_payment_id=data.clover_payment_id)
    db.add(sale); db.commit(); db.refresh(sale)
    return {"sale_id": sale.id, "amount": sale.amount, "status": sale.payment_status}

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
def list_members(db: Session = Depends(get_db), user: User = Depends(current_user)):
    members = db.query(Member).all()
    return [
        {
            "id": m.id,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "email": m.email,
            "phone": m.phone,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in members
    ]


@app.get("/api/sales")
def list_sales(db: Session = Depends(get_db), user: User = Depends(current_user)):
    sales = db.query(Sale).all()
    results = []

    for s in sales:
        rep = db.query(SalesRep).filter(SalesRep.id == s.sales_rep_id).first()
        member = db.query(Member).filter(Member.id == s.member_id).first()
        product = db.query(MembershipProduct).filter(MembershipProduct.id == s.product_id).first()

        results.append({
            "id": s.id,
            "member": f"{member.first_name} {member.last_name}" if member else "",
            "rep": rep.user.name if rep and rep.user else "",
            "membership": product.name if product else "",
            "amount": s.amount,
            "payment_status": s.payment_status,
            "sale_date": s.sale_date.isoformat() if s.sale_date else None,
            "clover_payment_id": s.clover_payment_id,
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
        "redirectUrls": {
            "success": "https://goldfish-app-jq38z.ondigitalocean.app?payment=success",
            "failure": "https://goldfish-app-jq38z.ondigitalocean.app?payment=failed",
            "cancel": "https://goldfish-app-jq38z.ondigitalocean.app?payment=cancelled",
        }
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

        if not name:
            continue

        existing = db.query(MembershipProduct).filter(MembershipProduct.name == name).first()

        if existing:
            existing.price = price_cents / 100
            existing.active = True
        else:
            product = MembershipProduct(
                name=name,
                price=price_cents / 100,
                active=True,
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


@app.post("/api/clover/webhook")
async def clover_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    print("========== CLOVER WEBHOOK ==========")
    print(payload)
    print("====================================")

    event_type = payload.get("type") or payload.get("eventType") or ""
    payment_id = payload.get("paymentId") or payload.get("id")
    checkout_id = payload.get("checkoutId") or payload.get("checkoutSessionId") or payload.get("orderId")

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
@app.get("/api/clover/settings")
def clover_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    settings = db.query(CloverSetting).first()
    return settings or {"merchant_id": "", "environment": "sandbox", "webhook_secret": ""}
