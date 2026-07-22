from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AcademyProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: Optional[str] = None
    level: str = "Fundamentals"
    age_group: str = "All Ages"


class AcademyProgramOut(AcademyProgramCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    active: bool
    created_at: datetime


class AcademyClassCreate(BaseModel):
    program_id: int
    name: str = Field(min_length=2, max_length=120)
    coach_name: Optional[str] = None
    weekday: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    capacity: int = Field(default=30, ge=1, le=500)


class AcademyClassOut(AcademyClassCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    active: bool
    created_at: datetime


class TrainingSessionCreate(BaseModel):
    academy_class_id: Optional[int] = None
    title: str = Field(min_length=2, max_length=160)
    coach_name: Optional[str] = None
    focus: Optional[str] = None
    attach_checked_in_members: bool = True


class TrainingSessionUpdate(BaseModel):
    status: Optional[str] = None
    focus: Optional[str] = None
    coach_notes: Optional[str] = None
    homework: Optional[str] = None


class ParticipantOut(BaseModel):
    id: int
    member_id: int
    member_name: str
    attended: bool
    performance_notes: Optional[str] = None


class TrainingSessionOut(BaseModel):
    id: int
    academy_class_id: Optional[int]
    title: str
    coach_name: Optional[str]
    focus: Optional[str]
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    coach_notes: Optional[str]
    homework: Optional[str]
    created_at: datetime
    participant_count: int = 0


class AcademyDashboardOut(BaseModel):
    active_programs: int
    active_classes: int
    sessions_today: int
    athletes_today: int
    recent_sessions: list[TrainingSessionOut]
