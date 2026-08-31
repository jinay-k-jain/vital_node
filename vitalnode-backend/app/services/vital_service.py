"""
Vital signs service.
Handles validation (technical validity, NOT clinical risk),
storage, and change detection for deterioration triggers.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
import uuid

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vital import Vital, VitalSource, AVPU
from app.models.encounter import Encounter
from app.schemas.assessment import VitalsCreate
from app.core.exceptions import InvalidVitalError
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Technical validity ranges ──────────────────────────────────────────────
# These are PHYSICAL plausibility bounds, NOT clinical risk thresholds.
# SpO2=91 is technically valid but clinically concerning - that's the
# clinical rules service's job to evaluate.
VITAL_BOUNDS = {
    "spo2":             (0.0, 100.0),
    "heart_rate":       (0.0, 500.0),
    "respiratory_rate": (0.0, 120.0),
    "bp_systolic":      (0.0, 400.0),
    "bp_diastolic":     (0.0, 300.0),
    "temperature":      (25.0, 45.0),
}

# Threshold for "stale" vitals (no new reading in this many minutes)
STALE_VITAL_MINUTES = 30


def validate_vitals(vitals: VitalsCreate) -> List[InvalidVitalError]:
    """
    Technical validation only.
    Returns a list of InvalidVitalError for any out-of-bounds values.
    Does NOT raise - caller decides whether to reject or warn.
    """
    errors: List[InvalidVitalError] = []
    fields = {
        "spo2": vitals.spo2,
        "heart_rate": vitals.heart_rate,
        "respiratory_rate": vitals.respiratory_rate,
        "bp_systolic": vitals.bp_systolic,
        "bp_diastolic": vitals.bp_diastolic,
        "temperature": vitals.temperature,
    }
    for field, value in fields.items():
        if value is None:
            continue
        lo, hi = VITAL_BOUNDS[field]
        if not (lo <= value <= hi):
            errors.append(
                InvalidVitalError(
                    field=field,
                    value=value,
                    reason=f"Value {value} is outside the technically valid range [{lo}, {hi}]",
                )
            )

    # BP sanity: diastolic must be less than systolic
    if vitals.bp_systolic is not None and vitals.bp_diastolic is not None:
        if vitals.bp_diastolic >= vitals.bp_systolic:
            errors.append(
                InvalidVitalError(
                    field="bp_diastolic",
                    value=vitals.bp_diastolic,
                    reason="Diastolic BP must be less than systolic BP",
                )
            )
    return errors


async def store_vital(
    db: AsyncSession,
    encounter_id: uuid.UUID,
    vitals_data: VitalsCreate,
    assessment_id: Optional[uuid.UUID] = None,
) -> Vital:
    """
    Store a new vital observation.
    Historical readings are never overwritten - every call creates a new row.
    """
    measured_at = vitals_data.measured_at or datetime.now(timezone.utc)
    device_id = None
    if vitals_data.device_id:
        try:
            device_id = uuid.UUID(vitals_data.device_id)
        except ValueError:
            pass

    vital = Vital(
        encounter_id=encounter_id,
        assessment_id=assessment_id,
        device_id=device_id,
        spo2=vitals_data.spo2,
        heart_rate=vitals_data.heart_rate,
        respiratory_rate=vitals_data.respiratory_rate,
        bp_systolic=vitals_data.bp_systolic,
        bp_diastolic=vitals_data.bp_diastolic,
        temperature=vitals_data.temperature,
        avpu=AVPU(vitals_data.avpu) if vitals_data.avpu else None,
        source=VitalSource(vitals_data.source),
        measured_at=measured_at,
    )
    db.add(vital)
    await db.flush()
    return vital


async def get_latest_vital(
    db: AsyncSession,
    encounter_id: uuid.UUID,
) -> Optional[Vital]:
    result = await db.execute(
        select(Vital)
        .where(Vital.encounter_id == encounter_id)
        .order_by(desc(Vital.measured_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_vital_history(
    db: AsyncSession,
    encounter_id: uuid.UUID,
    limit: int = 10,
) -> List[Vital]:
    result = await db.execute(
        select(Vital)
        .where(Vital.encounter_id == encounter_id)
        .order_by(desc(Vital.measured_at))
        .limit(limit)
    )
    return list(result.scalars().all())


def detect_deterioration(
    previous: Vital,
    current: Vital,
) -> Tuple[bool, List[str]]:
    """
    Compare two consecutive vital readings and return
    (deteriorated: bool, reasons: list[str]).
    Based on technically significant changes, NOT clinical diagnosis.
    """
    deteriorated = False
    reasons: List[str] = []

    if previous.spo2 is not None and current.spo2 is not None:
        delta = previous.spo2 - current.spo2
        if delta >= 3:  # drop of ≥3% is worth flagging
            deteriorated = True
            reasons.append(f"SpO₂ decreased from {previous.spo2}% to {current.spo2}%")

    if previous.heart_rate is not None and current.heart_rate is not None:
        delta = abs(current.heart_rate - previous.heart_rate)
        if delta >= 20:
            deteriorated = True
            reasons.append(
                f"Heart rate changed from {previous.heart_rate} to {current.heart_rate} bpm"
            )

    if previous.bp_systolic is not None and current.bp_systolic is not None:
        delta = previous.bp_systolic - current.bp_systolic
        if delta >= 20:
            deteriorated = True
            reasons.append(
                f"Systolic BP dropped from {previous.bp_systolic} to {current.bp_systolic} mmHg"
            )

    if previous.respiratory_rate is not None and current.respiratory_rate is not None:
        delta = abs(current.respiratory_rate - previous.respiratory_rate)
        if delta >= 6:
            deteriorated = True
            reasons.append(
                f"Respiratory rate changed from {previous.respiratory_rate} to {current.respiratory_rate}/min"
            )

    return deteriorated, reasons


def is_vital_stale(vital: Vital) -> bool:
    """Return True if the vital reading is older than STALE_VITAL_MINUTES."""
    age = datetime.now(timezone.utc) - vital.measured_at.replace(tzinfo=timezone.utc)
    return age > timedelta(minutes=STALE_VITAL_MINUTES)
