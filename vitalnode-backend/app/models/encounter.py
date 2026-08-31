"""
Encounter model - a single emergency visit.
One patient may have many encounters (repeat visits).
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class ArrivalMode(str, enum.Enum):
    WALK_IN = "walk-in"
    AMBULANCE = "ambulance"
    REFERRAL = "referral"
    TRANSFER = "transfer"
    OTHER = "other"


class PatientStatus(str, enum.Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    DISCHARGED = "DISCHARGED"
    ADMITTED = "ADMITTED"


class Acuity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    PENDING = "PENDING"


class SafetyStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    VERIFY = "VERIFY"
    URGENT_REVIEW = "URGENT_REVIEW"


class Encounter(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "encounters"

    # FK to patient
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Arrival details
    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_mode: Mapped[ArrivalMode] = mapped_column(
        SAEnum(ArrivalMode, name="arrivalmode", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    is_pregnant: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # only relevant for female patients

    # Current clinical state
    status: Mapped[PatientStatus] = mapped_column(
        SAEnum(PatientStatus, name="patientstatus"),
        default=PatientStatus.WAITING,
        nullable=False,
        index=True,
    )
    current_acuity: Mapped[Acuity] = mapped_column(
        SAEnum(Acuity, name="acuity"),
        default=Acuity.PENDING,
        nullable=False,
        index=True,
    )
    safety_status: Mapped[SafetyStatus] = mapped_column(
        SAEnum(SafetyStatus, name="safetystatus"),
        default=SafetyStatus.NORMAL,
        nullable=False,
    )

    # Queue
    waiting_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reassessment_due: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reassessment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Device
    device_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Surge
    is_surge_patient: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="encounters")  # type: ignore[name-defined]
    assessments: Mapped[List["Assessment"]] = relationship(  # type: ignore[name-defined]
        "Assessment", back_populates="encounter", cascade="all, delete-orphan"
    )
    vitals: Mapped[List["Vital"]] = relationship(  # type: ignore[name-defined]
        "Vital", back_populates="encounter", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(  # type: ignore[name-defined]
        "Notification", back_populates="encounter"
    )
    queue_entry: Mapped[Optional["QueueEntry"]] = relationship(  # type: ignore[name-defined]
        "QueueEntry", back_populates="encounter", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Encounter {self.id} patient={self.patient_id} status={self.status}>"
