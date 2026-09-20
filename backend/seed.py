import os
from dotenv import load_dotenv

load_dotenv()

from app.database import Base, engine, SessionLocal
from app.models import User, MembershipProduct, SalesRep, CloverSetting
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).filter(User.email == "admin@tngboxinggym.com").first():
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError("Set BOOTSTRAP_ADMIN_PASSWORD to at least 12 characters before seeding")
    admin = User(name="TNG Admin", email="admin@tngboxinggym.com", password_hash=hash_password(password), role="admin")
    db.add(admin)
products = [
    ("Pre-Sale Monthly", 155.00, True),
    ("Month-to-Month", 150.00, True),
    ("3 Months Special", 300.00, False),
    ("Full Year", 900.00, False),
]
for name, price, recurring in products:
    if not db.query(MembershipProduct).filter(MembershipProduct.name == name).first():
        months = 12 if name == "Full Year" else 3 if name == "3 Months Special" else 1
        db.add(MembershipProduct(name=name, price=price, recurring=recurring, active=True,
                                 category="membership", is_membership=True,
                                 default_membership_months=months, renews_monthly=recurring))
if not db.query(CloverSetting).first():
    db.add(CloverSetting())
db.commit(); db.close()
print("Seed complete. Existing accounts and products were preserved.")
