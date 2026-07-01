from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
import base64, io, qrcode
from .database import Base, engine, get_db
from .models import User, SalesRep, Member, MembershipProduct, Sale, CloverSetting
from .schemas import LoginIn, RepCreate, SaleCreate
from .auth import verify_password, hash_password, create_token, decode_token
from .commission import commission_rate

Base.metadata.create_all(bind=engine)
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
    url = f"https://crm.tngboxinggym.com/join/{rep.referral_slug}"
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
@app.post("/api/clover/webhook")
async def clover_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    # TODO: verify Clover signature using webhook secret after deployment.
    # TODO: match checkout/order metadata to referral_slug or rep_id.
    return {"received": True, "note": "Webhook received. Signature verification and sale matching should be enabled before production.", "payload_preview": payload}

@app.get("/api/clover/settings")
def clover_settings(db: Session = Depends(get_db), user: User = Depends(current_user)):
    require_admin(user)
    settings = db.query(CloverSetting).first()
    return settings or {"merchant_id": "", "environment": "sandbox", "webhook_secret": ""}
