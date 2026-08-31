"""
Patient model - represents a real-world patient identity.
A patient may have multiple emergency encounters.
"""
import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Sex(str, enum.Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class AgeGroup(str, enum.Enum):
    PEDIATRIC = "PEDIATRIC"
    ADULT = "ADULT"
    OLDER_ADULT = "OLDER_ADULT"


class Patient(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "patients"

    # Display identifier shown in UI (e.g., P-10241)
    display_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Demographics
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[Sex] = mapped_column(
        SAEnum(Sex, name="sex", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    age_group: Mapped[AgeGroup] = mapped_column(
        SAEnum(AgeGroup, name="agegroup"),
        nullable=False,
    )
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    encounters: Mapped[List["Encounter"]] = relationship(  # type: ignore[name-defined]
        "Encounter", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patient {self.display_id} age={self.age}>"
