"""
Vital signs model.
Each reading is stored as a new record - historical readings are never overwritten.
This enables deterioration detection by comparing sequential readings.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class VitalSource(str, enum.Enum):
    MANUAL = "Manual Entry"
    DEVICE = "Connected Device"
    IMPORTED = "Imported"


class AVPU(str, enum.Enum):
    ALERT = "Alert"
    VOICE = "Voice"
    PAIN = "Pain"
    UNRESPONSIVE = "Unresponsive"


class Vital(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "vitals"

    # Links
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True
    )
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )

    # Vital values — all nullable; missing data is explicit NOT assumed
    spo2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)          # %
    heart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # bpm
    respiratory_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # /min
    bp_systolic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # mmHg
    bp_diastolic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mmHg
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # °C
    avpu: Mapped[Optional[AVPU]] = mapped_column(
        SAEnum(AVPU, name="avpu", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Source metadata
    source: Mapped[VitalSource] = mapped_column(
        SAEnum(VitalSource, name="vitalsource", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=VitalSource.MANUAL,
    )
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="vitals")  # type: ignore[name-defined]
    assessment: Mapped[Optional["Assessment"]] = relationship("Assessment", back_populates="vitals")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<Vital spo2={self.spo2} hr={self.heart_rate} "
            f"rr={self.respiratory_rate} bp={self.bp_systolic}/{self.bp_diastolic}>"
        )
