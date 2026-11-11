"""The membership plans exposed by the public signup pages."""
from app.models import MembershipProduct
from sqlalchemy import func


def public_join_products(db):
    return db.query(MembershipProduct).filter(MembershipProduct.active==True,MembershipProduct.is_membership==True,MembershipProduct.price.in_([150,300,999])).order_by(MembershipProduct.price.asc()).all()


def public_registration_fee(db):
    return db.query(MembershipProduct).filter(func.lower(MembershipProduct.name)=='registration fee',MembershipProduct.active==True).first()
