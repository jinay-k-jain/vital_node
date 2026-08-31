"""
User model - staff accounts with role-based access.
Roles mirror the frontend: Triage Nurse | Clinician | Administrator
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    TRIAGE_NURSE = "Triage Nurse"
    CLINICIAN = "Clinician"
    ADMINISTRATOR = "Administrator"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    staff_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="Emergency")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    audit_events: Mapped[List["AuditEvent"]] = relationship(  # type: ignore[name-defined]
        "AuditEvent", back_populates="user", foreign_keys="AuditEvent.user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.staff_id} ({self.role})>"
