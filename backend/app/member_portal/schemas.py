from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ActivateMemberIn(BaseModel):
    token: str
    password: str = Field(min_length=8)


class InviteMemberIn(BaseModel):
    member_id: int


class LinkInBodyIn(BaseModel):
    inbody_user_id: str
    consent: bool = True


class ManualInBodyScanIn(BaseModel):
    scan_date: datetime
    weight: Optional[float] = None
    skeletal_muscle_mass: Optional[float] = None
    body_fat_mass: Optional[float] = None
    percent_body_fat: Optional[float] = None
    bmi: Optional[float] = None
    visceral_fat_level: Optional[float] = None
    bmr: Optional[float] = None
    inbody_score: Optional[float] = None

