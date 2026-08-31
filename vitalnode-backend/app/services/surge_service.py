"""Deterministic, API-free synthetic arrivals for the demo surge scenario."""
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentType, HistoryStatus
from app.models.encounter import Acuity, ArrivalMode, Encounter, PatientStatus, SafetyStatus
from app.models.patient import AgeGroup, Patient, Sex
from app.models.queue_entry import QueueEntry
from app.models.vital import AVPU, Vital, VitalSource
from app.schemas.assessment import NurseDecisionCreate
from app.services.assessment_service import record_nurse_decision, run_ai_assessment


SURGE_TEMPLATES = (
    {"complaint": "Severe chest pain with sweating", "symptoms": ["Chest pain", "Diaphoresis"], "danger_signs": ["Severe distress"], "vitals": (90, 124, 28, 88, 60, 37.1, "Alert"), "age": 58, "sex": Sex.MALE},
    {"complaint": "Breathing difficulty and wheezing", "symptoms": ["Dyspnea", "Wheezing"], "danger_signs": ["Breathing difficulty"], "vitals": (91, 118, 29, 104, 68, 37.8, "Alert"), "age": 34, "sex": Sex.FEMALE},
    {"complaint": "High fever and headache", "symptoms": ["Fever", "Headache"], "danger_signs": [], "vitals": (97, 102, 20, 118, 76, 39.4, "Alert"), "age": 42, "sex": Sex.MALE},
    {"complaint": "Minor ankle injury", "symptoms": ["Ankle pain", "Swelling"], "danger_signs": [], "vitals": (99, 76, 16, 118, 72, 36.8, "Alert"), "age": 27, "sex": Sex.FEMALE},
    {"complaint": "Found unconscious with unknown history", "symptoms": ["Altered consciousness", "Unknown history"], "danger_signs": ["Altered consciousness"], "vitals": (94, 108, 24, 96, 62, 36.1, "Pain"), "age": 33, "sex": Sex.UNKNOWN},
)


def _age_group(age: int) -> AgeGroup:
    return AgeGroup.PEDIATRIC if age < 18 else AgeGroup.OLDER_ADULT if age >= 65 else AgeGroup.ADULT


async def create_surge_patients(db: AsyncSession, user, count: int) -> int:
    """Create, score, and queue synthetic records without calling Gemini."""
    if count <= 0:
        return 0
    existing = await db.scalar(select(func.count()).select_from(Patient)) or 0
    now = datetime.now(timezone.utc)
    for index in range(count):
        template = SURGE_TEMPLATES[index % len(SURGE_TEMPLATES)]
        age = template["age"]
        patient = Patient(
            display_id=f"P-SURGE{existing + index + 1:03d}", name=f"Surge Patient {index + 1}",
            age=age, sex=template["sex"], age_group=_age_group(age), is_simulation=True,
        )
        db.add(patient)
        await db.flush()
        arrival = now - timedelta(minutes=(index * 3) % 30)
        encounter = Encounter(
            patient_id=patient.id, arrival_time=arrival, arrival_mode=ArrivalMode.WALK_IN,
            status=PatientStatus.WAITING, current_acuity=Acuity.PENDING, safety_status=SafetyStatus.NORMAL,
            waiting_time_seconds=int((now - arrival).total_seconds()), reassessment_count=0,
            last_updated=now, device_connected=False, is_surge_patient=True,
        )
        db.add(encounter)
        await db.flush()
        assessment = Assessment(
            encounter_id=encounter.id, assessment_type=AssessmentType.INITIAL,
            chief_complaint=template["complaint"], confirmed_complaint=template["complaint"],
            symptoms=template["symptoms"], danger_signs=template["danger_signs"],
            none_observed=not template["danger_signs"], history_status=HistoryStatus.UNAVAILABLE,
            history_conditions=[], history_medications=[], history_allergies=[], submitted_by_id=user.id, submitted_at=arrival,
        )
        db.add(assessment)
        await db.flush()
        vitals = template["vitals"]
        db.add(Vital(
            encounter_id=encounter.id, assessment_id=assessment.id, spo2=vitals[0], heart_rate=vitals[1],
            respiratory_rate=vitals[2], bp_systolic=vitals[3], bp_diastolic=vitals[4], temperature=vitals[5],
            avpu=AVPU(vitals[6]), source=VitalSource.MANUAL, measured_at=arrival,
        ))
        db.add(QueueEntry(encounter_id=encounter.id, priority_score=999, acuity_rank=4,
                          reassessment_overdue=False, has_safety_flag=False, last_priority_update=now))
        await db.flush()
        recommendation = await run_ai_assessment(
            db, assessment, encounter, user.id, user.staff_id, user.name, user.role.value,
        )
        # Synthetic arrivals are explicitly auto-accepted so they enter the demo queue.
        await record_nurse_decision(
            db, assessment, encounter,
            NurseDecisionCreate(action="ACCEPTED", final_acuity=recommendation.acuity.value),
            user.id, user.staff_id, user.name, user.role.value,
        )
    return count
