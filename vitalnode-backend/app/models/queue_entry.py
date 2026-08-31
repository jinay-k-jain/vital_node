"""
QueueEntry model - the patient's current position in the triage queue.
One entry per active encounter. Updated by the queue service after each
nurse decision, vital update, or reassessment.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class QueueEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "queue_entries"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("encounters.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Computed priority score (lower = higher priority)
    # Formula: acuity_rank * 1000 - waiting_time_bonus + safety_penalty
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=999.0, index=True)

    # Derived from encounter
    acuity_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    # 0=CRITICAL, 1=HIGH, 2=MODERATE, 3=LOW, 4=PENDING

    reassessment_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_safety_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_priority_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationship
    encounter: Mapped["Encounter"] = relationship("Encounter", back_populates="queue_entry")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<QueueEntry encounter={self.encounter_id} priority={self.priority_score}>"
