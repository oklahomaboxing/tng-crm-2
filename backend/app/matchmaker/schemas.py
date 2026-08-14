from typing import Optional
from pydantic import BaseModel

class FighterCreate(BaseModel):
    legal_name: str
    dob: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    stance: str = ""
    gym: str = ""
    coach: str = ""
    height_in: Optional[int] = None
    reach_in: Optional[int] = None
    walk_weight: Optional[float] = None
    fight_weight: Optional[float] = None
    pro_record: str = ""
    amateur_record: str = ""
    boxrec_id: str = ""
    boxrec_url: str = ""
    instagram: str = ""
    facebook: str = ""
    tiktok: str = ""
    twitter: str = ""
    submitted_by_name: str = ""
    submitted_by_role: str = ""
    submitted_by_phone: str = ""
    submitted_by_email: str = ""
    manager_name: str = ""
    manager_phone: str = ""
    manager_email: str = ""
    ok_license_status: str = "unknown"
    federal_id_status: str = "unknown"
    suspension_status: str = "needs_review"
    bloodwork_status: str = "missing"
    bloodwork_expires: str = ""
    available: bool = True
    available_weight_min: Optional[float] = None
    available_weight_max: Optional[float] = None
    last_fight_date: str = ""

class EventCreate(BaseModel):
    slug: str
    name: str
    venue: str = ""
    venue_address: str = ""
    event_date: str = ""

class BoutCreate(BaseModel):
    event_id: Optional[int] = None
    red_fighter_id: int
    blue_fighter_id: int
    weight_agreed: Optional[float] = None
    rounds: int = 4
    bout_type: str = "pro"
    red_purse: float = 0
    blue_purse: float = 0
    match_score: Optional[int] = None
    notes: str = ""


class PublicFighterRegistration(BaseModel):
    submitted_by_role: str = "boxer"
    submitted_by_name: str = ""
    submitted_by_phone: str = ""
    submitted_by_email: str = ""

    boxrec_id: str = ""
    legal_name: str

    pro_record: str = ""
    stance: str = ""
    gym: str = ""

    city: str = ""
    state: str = ""
    country: str = "USA"

    phone: str = ""
    email: str = ""

    instagram: str = ""
    facebook: str = ""
    tiktok: str = ""
    twitter: str = ""

    available_weight_min: Optional[float] = None
    available_weight_max: Optional[float] = None
    fight_weight: Optional[float] = None
