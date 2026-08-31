"""
Patient + Encounter service.
Creates patients, encounters and the canonical FullPatientResponse shape
consumed by the frontend.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patient import Patient, AgeGroup
from app.models.encounter import Encounter, ArrivalMode, PatientStatus, Acuity, SafetyStatus
from app.models.assessment import Assessment, AssessmentType, HistoryStatus
from app.models.vital import Vital, VitalSource, AVPU
from app.models.recommendation import AIRecommendation, NurseDecision
from app.models.queue_entry import QueueEntry
from app.schemas.assessment import AssessmentCreate
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

ACUITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "PENDING": 4}


def _get_age_group(age: int) -> AgeGroup:
    if age < 18:
        return AgeGroup.PEDIATRIC
    if age >= 65:
        return AgeGroup.OLDER_ADULT
    return AgeGroup.ADULT


def _next_display_id(current_count: int) -> str:
    return f"P-{10241 + current_count}"


async def create_patient_and_encounter(
    db: AsyncSession,
    payload: AssessmentCreate,
    submitted_by_id: uuid.UUID,
) -> tuple[Patient, Encounter, Assessment]:
    """
    Full intake flow:
    1. Create Patient record
    2. Create Encounter
    3. Create initial Assessment (danger signs, history, complaint, symptoms)
    4. Create Vital record
    5. Create QueueEntry
    Returns (patient, encounter, assessment)
    """
    # Reassessment: keep the same patient and encounter, append clinical data.
    # This deliberately does not create a new queue entry or reset arrival time.
    if payload.reassessment_encounter_id:
        try:
            encounter_id = uuid.UUID(payload.reassessment_encounter_id)
        except ValueError as exc:
            raise ValueError("Invalid reassessment encounter ID") from exc

        result = await db.execute(
            select(Encounter)
            .options(selectinload(Encounter.patient), selectinload(Encounter.vitals))
            .where(Encounter.id == encounter_id)
        )
        encounter = result.scalar_one_or_none()
        if not encounter or not encounter.patient:
            raise ValueError("Reassessment encounter was not found")

        now = datetime.now(timezone.utc)
        patient = encounter.patient
        previous_result = await db.execute(
            select(Assessment)
            .where(Assessment.encounter_id == encounter.id)
            .order_by(Assessment.created_at.desc())
            .limit(1)
        )
        previous = previous_result.scalar_one_or_none()
        assessment = Assessment(
            encounter_id=encounter.id,
            assessment_type=AssessmentType.REASSESSMENT,
            chief_complaint=payload.chief_complaint,
            voice_transcript=payload.voice_transcript,
            confirmed_complaint=payload.chief_complaint,
            symptoms=payload.symptoms,
            danger_signs=payload.danger_signs,
            none_observed=payload.none_observed,
            # Retain the original patient context; reassessment only replaces
            # the current clinical observations.
            history_status=previous.history_status if previous else HistoryStatus.UNAVAILABLE,
            history_conditions=previous.history_conditions if previous else [],
            history_medications=previous.history_medications if previous else [],
            history_allergies=previous.history_allergies if previous else [],
            history_notes=previous.history_notes if previous else None,
            raw_extracted_symptoms=(
                previous.raw_extracted_symptoms
                if previous and payload.chief_complaint == (previous.confirmed_complaint or previous.chief_complaint)
                else None
            ),
            submitted_by_id=submitted_by_id, submitted_at=now,
        )
        db.add(assessment)
        await db.flush()
        v = payload.vitals
        vital = Vital(
            encounter_id=encounter.id, assessment_id=assessment.id,
            spo2=v.spo2, heart_rate=v.heart_rate, respiratory_rate=v.respiratory_rate,
            bp_systolic=v.bp_systolic, bp_diastolic=v.bp_diastolic,
            temperature=v.temperature, avpu=AVPU(v.avpu) if v.avpu else None,
            source=VitalSource(v.source), measured_at=v.measured_at or now,
        )
        db.add(vital)
        encounter.last_updated = now
        encounter.device_connected = payload.vitals.source == "Connected Device"
        await db.flush()
        return patient, encounter, assessment

    # Count existing patients for display ID
    count_result = await db.execute(select(func.count()).select_from(Patient))
    count = count_result.scalar() or 0

    age_group = _get_age_group(payload.age)

    # 1. Patient
    patient = Patient(
        display_id=_next_display_id(count),
        name=payload.name,
        age=payload.age,
        sex=payload.sex,  # type: ignore
        age_group=age_group,
        is_simulation=True,
    )
    db.add(patient)
    await db.flush()

    # 2. Encounter
    now = datetime.now(timezone.utc)
    encounter = Encounter(
        patient_id=patient.id,
        arrival_time=now,
        arrival_mode=ArrivalMode(payload.arrival_mode),
        is_pregnant=payload.is_pregnant,
        status=PatientStatus.WAITING,
        current_acuity=Acuity.PENDING,
        safety_status=SafetyStatus.NORMAL,
        waiting_time_seconds=0,
        reassessment_count=0,
        last_updated=now,
        device_connected=payload.vitals.source == "Connected Device",
    )
    db.add(encounter)
    await db.flush()

    # 3. Assessment — auto-lookup history from pre-loaded records
    from app.data.patient_history_records import lookup_patient_history
    history_record = lookup_patient_history(payload.name or "", payload.age)

    if history_record:
        history_status = HistoryStatus.AVAILABLE
        history_conditions = history_record["conditions"]
        history_medications = history_record["medications"]
        history_allergies = history_record["allergies"]
        history_notes = history_record["history_text"]
    else:
        history_status = HistoryStatus.UNAVAILABLE
        history_conditions = []
        history_medications = []
        history_allergies = []
        history_notes = None

    assessment = Assessment(
        encounter_id=encounter.id,
        assessment_type=AssessmentType.INITIAL,
        chief_complaint=payload.chief_complaint,
        voice_transcript=payload.voice_transcript,
        confirmed_complaint=payload.chief_complaint,
        symptoms=payload.symptoms,
        danger_signs=payload.danger_signs,
        none_observed=payload.none_observed,
        history_status=history_status,
        history_conditions=history_conditions,
        history_medications=history_medications,
        history_allergies=history_allergies,
        history_notes=history_notes,
        submitted_by_id=submitted_by_id,
        submitted_at=now,
    )
    db.add(assessment)
    await db.flush()

    # 4. Vital
    v = payload.vitals
    measured_at = v.measured_at or now
    vital = Vital(
        encounter_id=encounter.id,
        assessment_id=assessment.id,
        spo2=v.spo2,
        heart_rate=v.heart_rate,
        respiratory_rate=v.respiratory_rate,
        bp_systolic=v.bp_systolic,
        bp_diastolic=v.bp_diastolic,
        temperature=v.temperature,
        avpu=AVPU(v.avpu) if v.avpu else None,
        source=VitalSource(v.source),
        measured_at=measured_at,
    )
    db.add(vital)
    await db.flush()

    # 5. QueueEntry
    queue_entry = QueueEntry(
        encounter_id=encounter.id,
        priority_score=999.0,
        acuity_rank=4,  # PENDING
        reassessment_overdue=False,
        has_safety_flag=False,
        last_priority_update=now,
    )
    db.add(queue_entry)
    await db.flush()

    logger.info(
        "patient_created",
        display_id=patient.display_id,
        encounter_id=str(encounter.id),
    )
    return patient, encounter, assessment


async def get_encounter_with_latest_vitals(
    db: AsyncSession,
    encounter_id: uuid.UUID,
) -> Optional[Encounter]:
    result = await db.execute(
        select(Encounter)
        .options(
            selectinload(Encounter.patient),
            selectinload(Encounter.assessments).selectinload(Assessment.ai_recommendation),
            selectinload(Encounter.assessments).selectinload(Assessment.nurse_decision),
            selectinload(Encounter.vitals),
        )
        .where(Encounter.id == encounter_id)
    )
    return result.scalar_one_or_none()


async def search_patients(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> List[Patient]:
    q = f"%{query.lower()}%"
    result = await db.execute(
        select(Patient)
        .where(
            or_(
                func.lower(Patient.display_id).like(q),
                func.lower(Patient.name).like(q),
            )
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_encounter_priority(
    db: AsyncSession,
    encounter: Encounter,
    new_acuity: Acuity,
    safety_status: SafetyStatus,
    reassessment_overdue: bool = False,
) -> None:
    """Recompute queue priority after acuity change."""
    rank = ACUITY_RANK.get(new_acuity.value, 4)
    safety_bonus = 100 if safety_status == SafetyStatus.URGENT_REVIEW else 0
    overdue_bonus = 50 if reassessment_overdue else 0
    # Lower score = higher priority
    priority_score = rank * 1000 - safety_bonus - overdue_bonus

    encounter.current_acuity = new_acuity
    encounter.safety_status = safety_status
    encounter.last_updated = datetime.now(timezone.utc)

    # Update queue entry
    result = await db.execute(
        select(QueueEntry).where(QueueEntry.encounter_id == encounter.id)
    )
    qe = result.scalar_one_or_none()
    if qe:
        qe.priority_score = priority_score
        qe.acuity_rank = rank
        qe.has_safety_flag = safety_status != SafetyStatus.NORMAL
        qe.reassessment_overdue = reassessment_overdue
        qe.last_priority_update = datetime.now(timezone.utc)

    await db.flush()


async def set_reassessment_due(
    db: AsyncSession,
    encounter: Encounter,
    acuity: str,
) -> None:
    """Set the reassessment timer based on acuity."""
    interval_min = settings.reassessment_interval_minutes(acuity)
    encounter.reassessment_due = datetime.now(timezone.utc) + timedelta(minutes=interval_min)
    await db.flush()
