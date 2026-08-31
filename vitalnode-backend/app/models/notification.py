"""
Notification model - in-app alerts for clinical events.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class NotificationType(str, enum.Enum):
    REASSESSMENT_DUE = "REASSESSMENT_DUE"
    VITAL_RECEIVED = "VITAL_RECEIVED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    DEVICE_DISCONNECTED = "DEVICE_DISCONNECTED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notificationtype"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Target encounter/patient
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=True, index=True
    )
    patient_display_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Target user (null = broadcast to all in department)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter", back_populates="notifications")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Notification {self.type} read={self.is_read}>"
