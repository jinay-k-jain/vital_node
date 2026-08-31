"""
AIRecommendation model - the output of the full AI pipeline.
Immutable once created. New recommendations create new records.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.encounter import Acuity, SafetyStatus


class ModelStatus(str, enum.Enum):
    MOCK = "MOCK"
    ACTIVE = "ACTIVE"
    UNAVAILABLE = "UNAVAILABLE"


class AIRecommendation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_recommendations"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Recommendation output
    acuity: Mapped[Acuity] = mapped_column(SAEnum(Acuity, name="acuity"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    data_completeness: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100

    # Safety gate output
    safety_status: Mapped[SafetyStatus] = mapped_column(SAEnum(SafetyStatus, name="safetystatus"), nullable=False)
    safety_flag: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Explanation arrays (stored as JSON)
    key_reasons: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    clinical_rules: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    top_factors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [{feature, value, impact, direction}]

    # Model provenance
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="mock-v1.0")
    model_status: Mapped[ModelStatus] = mapped_column(
        SAEnum(ModelStatus, name="modelstatus"),
        default=ModelStatus.MOCK,
        nullable=False,
    )
    clinical_rule_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0")

    # Conservative flag (applied when data is incomplete or pathway is pediatric)
    is_conservative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamp of when the recommendation was generated
    recommended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="ai_recommendation")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<AIRecommendation acuity={self.acuity} confidence={self.confidence}>"


class NurseDecision(Base, UUIDMixin, TimestampMixin):
    """
    Nurse's final decision after reviewing the AI recommendation.
    The AI recommendation is NEVER deleted on override.
    """
    __tablename__ = "nurse_decisions"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    nurse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    action: Mapped[str] = mapped_column(String(50), nullable=False)  # ACCEPTED | OVERRIDE | REASSESS_REQUESTED
    final_acuity: Mapped[Acuity] = mapped_column(SAEnum(Acuity, name="acuity"), nullable=False)

    # Override-specific fields
    override_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    override_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="nurse_decision")  # type: ignore[name-defined]
    nurse: Mapped[Optional["User"]] = relationship("User")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<NurseDecision action={self.action} final_acuity={self.final_acuity}>"
