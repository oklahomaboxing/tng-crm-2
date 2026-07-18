from datetime import date
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


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    product_id: Optional[int] = None
    referral_slug: Optional[str] = None


class WaiverSubmissionCreate(BaseModel):
    lead_id: int

    participant_first_name: str
    participant_last_name: str
    participant_date_of_birth: date

    guardian_name: Optional[str] = None
    signer_relationship: str = "self"

    emergency_contact_name: str
    emergency_contact_phone: str

    waiver_accepted: bool
    medical_acknowledgment: bool

    signature_name: str
    signature_data: Optional[str] = None

    photo_release: bool = False
    sms_consent: bool = False
    email_consent: bool = False
