"""
AuditEvent model - immutable record of all clinical and system actions.
Records are insert-only. Updates and deletes are forbidden by application logic.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.base import UUIDMixin
from app.models.encounter import Acuity


class AuditEvent(Base, UUIDMixin):
    """
    Immutable audit record. No updated_at by design.
    All clinical events, AI predictions, nurse decisions, overrides
    and system events are logged here.
    """
    __tablename__ = "audit_events"

    # When it happened
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Who
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_staff_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # denormalised for audit immutability
    user_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # What
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. LOGIN | LOGOUT | PATIENT_CREATED | ASSESSMENT_CREATED | AI_PREDICTION |
    #       ACCEPTED | OVERRIDE | REASSESS_REQUESTED | VITAL_UPDATED | DEVICE_EVENT |
    #       SURGE_STARTED | SURGE_STOPPED | CONFIG_CHANGED

    # Which patient/encounter (nullable for non-clinical events)
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_display_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
    )
    assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Clinical details (denormalised for immutable audit trail)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Acuity value
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    safety_flag: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nurse_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    final_acuity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Flexible metadata for system/device events
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships (read-only, no cascade)
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_events")  # type: ignore[name-defined]

    __table_args__ = (
        Index("ix_audit_events_patient_timestamp", "patient_id", "timestamp"),
        Index("ix_audit_events_event_type_timestamp", "event_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent {self.event_type} user={self.user_staff_id} at={self.timestamp}>"
