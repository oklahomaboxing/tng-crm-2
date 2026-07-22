from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class AcademyProgram(Base):
    __tablename__ = "academy_programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    level = Column(String(40), nullable=False, default="Fundamentals")
    age_group = Column(String(40), nullable=False, default="All Ages")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    classes = relationship("AcademyClass", back_populates="program", cascade="all, delete-orphan")


class AcademyClass(Base):
    __tablename__ = "academy_classes"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("academy_programs.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    coach_name = Column(String(120), nullable=True)
    weekday = Column(String(20), nullable=True)
    start_time = Column(String(10), nullable=True)
    end_time = Column(String(10), nullable=True)
    capacity = Column(Integer, nullable=False, default=30)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    program = relationship("AcademyProgram", back_populates="classes")
    sessions = relationship("TrainingSession", back_populates="academy_class", cascade="all, delete-orphan")


class TrainingSession(Base):
    __tablename__ = "academy_training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    academy_class_id = Column(Integer, ForeignKey("academy_classes.id"), nullable=True, index=True)
    title = Column(String(160), nullable=False)
    coach_name = Column(String(120), nullable=True)
    focus = Column(String(160), nullable=True)
    status = Column(String(30), nullable=False, default="scheduled")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    coach_notes = Column(Text, nullable=True)
    homework = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    academy_class = relationship("AcademyClass", back_populates="sessions")
    participants = relationship(
        "TrainingSessionParticipant",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class TrainingSessionParticipant(Base):
    __tablename__ = "academy_training_session_participants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("academy_training_sessions.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    attended = Column(Boolean, nullable=False, default=True)
    performance_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("TrainingSession", back_populates="participants")
