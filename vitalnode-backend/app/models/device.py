"""
Device model - simulated medical device gateway.
Real devices should connect through this abstraction, never directly to the frontend.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class DeviceStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    SIMULATED = "SIMULATED"


class Device(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "devices"

    device_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(
        SAEnum(DeviceStatus, name="devicestatus"),
        default=DeviceStatus.SIMULATED,
        nullable=False,
    )

    # Assigned encounter (if any)
    encounter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True
    )

    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Device {self.device_code} status={self.status}>"
