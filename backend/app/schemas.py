from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class RepCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = "TNG12345"
    phone: str = ""
    referral_slug: str
    clover_link: str = ""

class SaleCreate(BaseModel):
    member_first_name: str
    member_last_name: str
    member_email: str = ""
    member_phone: str = ""
    sales_rep_id: int
    product_id: int
    clover_order_id: str = ""
    clover_payment_id: str = ""
    payment_status: str = "paid"
