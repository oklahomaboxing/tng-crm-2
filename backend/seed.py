from app.database import Base, engine, SessionLocal
from app.models import User, MembershipProduct, SalesRep, CloverSetting
from app.auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).filter(User.email == "admin@tngboxinggym.com").first():
    admin = User(name="TNG Admin", email="admin@tngboxinggym.com", password_hash=hash_password("admin123"), role="admin")
    db.add(admin)
products = [
    ("Pre-Sale Monthly", 155.00, True),
    ("Month-to-Month", 150.00, True),
    ("3 Months Special", 300.00, False),
    ("Full Year", 900.00, False),
]
for name, price, recurring in products:
    if not db.query(MembershipProduct).filter(MembershipProduct.name == name).first():
        db.add(MembershipProduct(name=name, price=price, recurring=recurring, active=True))
if not db.query(User).filter(User.email == "rep@tngboxinggym.com").first():
    rep_user = User(name="Demo Sales Rep", email="rep@tngboxinggym.com", password_hash=hash_password("rep123"), role="rep")
    db.add(rep_user); db.flush()
    db.add(SalesRep(user_id=rep_user.id, phone="", referral_slug="demo", clover_link="https://www.clover.com/online-ordering/demo"))
if not db.query(CloverSetting).first():
    db.add(CloverSetting())
db.commit(); db.close()
print("Seed complete. Admin: admin@tngboxinggym.com / admin123 | Rep: rep@tngboxinggym.com / rep123")
