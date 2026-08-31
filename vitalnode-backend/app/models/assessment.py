"""
Assessment model - a complete clinical triage assessment.
One encounter may have multiple assessments (initial + reassessments).
Fields mirror the frontend NewAssessmentScreen form exactly.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class AssessmentType(str, enum.Enum):
    INITIAL = "INITIAL"
    REASSESSMENT = "REASSESSMENT"


class HistoryStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PARTIAL = "PARTIAL"


class Assessment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assessments"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_type: Mapped[AssessmentType] = mapped_column(
        SAEnum(AssessmentType, name="assessmenttype"),
        default=AssessmentType.INITIAL,
        nullable=False,
    )

    # Chief complaint
    chief_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # raw voice
    confirmed_complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # nurse-confirmed

    # Symptoms (JSON array of strings - nurse-confirmed after extraction)
    symptoms: Mapped[Optional[List]] = mapped_column(JSON, nullable=True, default=list)
    raw_extracted_symptoms: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)  # NLP extracted, pre-confirmation

    # Danger signs (JSON array of string IDs)
    danger_signs: Mapped[Optional[List]] = mapped_column(JSON, nullable=True, default=list)
    none_observed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Patient history
    history_status: Mapped[HistoryStatus] = mapped_column(
        SAEnum(HistoryStatus, name="historystatus"),
        default=HistoryStatus.UNAVAILABLE,
        nullable=False,
    )
    history_conditions: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    history_medications: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    history_allergies: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    history_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Submitted by
    submitted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="assessments")  # type: ignore[name-defined]
    vitals: Mapped[List["Vital"]] = relationship(  # type: ignore[name-defined]
        "Vital", back_populates="assessment"
    )
    ai_recommendation: Mapped[Optional["AIRecommendation"]] = relationship(  # type: ignore[name-defined]
        "AIRecommendation", back_populates="assessment", uselist=False
    )
    nurse_decision: Mapped[Optional["NurseDecision"]] = relationship(  # type: ignore[name-defined]
        "NurseDecision", back_populates="assessment", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Assessment {self.id} type={self.assessment_type}>"
