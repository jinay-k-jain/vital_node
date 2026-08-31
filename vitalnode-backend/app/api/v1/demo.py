from app.api.v1.utils import ev
"""
Demo Scenario API - /api/v1/demo/*
Only available when DEMO_MODE=true in .env

These endpoints allow triggering specific patient scenarios for demonstration.
NEVER expose in production.
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import DbDep, CurrentUser
from app.core.config import get_settings
from app.core.exceptions import DemoModeError
from app.models.encounter import Encounter, PatientStatus
from app.models.vital import Vital, VitalSource, AVPU
from app.services.notification_service import create_notification
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/demo", tags=["Demo Scenarios"])
settings = get_settings()


def _guard_demo():
    if not settings.demo_mode:
        raise DemoModeError()


@router.get("/scenarios", summary="List available demo scenarios")
async def list_scenarios(current_user: CurrentUser):
    _guard_demo()
    return {
        "scenarios": [
            {"id": "critical-patient",    "name": "Critical adult – chest pain, shock"},
            {"id": "ambiguous-patient",   "name": "Ambiguous presentation – low confidence"},
            {"id": "pediatric-patient",   "name": "Pediatric patient – high fever"},
            {"id": "zero-history",        "name": "Zero-history patient – unconscious"},
            {"id": "deterioration",       "name": "Simulate patient deterioration"},
            {"id": "surge",               "name": "Activate 3× surge mode"},
        ],
        "note": "Demo scenarios are clearly marked SIMULATION. Not for real patient care.",
    }


@router.post("/reset", summary="Reset all demo data (clears seeded patients)")
async def reset_demo(db: DbDep, current_user: CurrentUser):
    """
    Marks all simulation encounters as DISCHARGED so they leave the queue.
    Does NOT delete audit records (audit is immutable).
    """
    _guard_demo()
    result = await db.execute(
        select(Encounter)
        .options(selectinload(Encounter.patient))
        .where(Encounter.is_surge_patient == False)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
    )
    encounters = result.scalars().all()
    count = 0
    for enc in encounters:
        if enc.patient and enc.patient.is_simulation:
            enc.status = PatientStatus.DISCHARGED
            count += 1

    await record_audit_event(
        db=db,
        event_type="DEMO_RESET",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
        metadata={"encounters_cleared": count},
    )

    return {"message": f"Demo reset complete. {count} simulation encounters discharged."}


@router.post("/simulate-deterioration/{encounter_id}", summary="Simulate patient deterioration")
async def simulate_deterioration(encounter_id: str, db: DbDep, current_user: CurrentUser):
    """Push worsening vitals to an encounter to demonstrate the deterioration pipeline."""
    _guard_demo()
    import uuid
    try:
        eid = uuid.UUID(encounter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid encounter ID"})

    result = await db.execute(
        select(Encounter)
        .options(selectinload(Encounter.patient))
        .where(Encounter.id == eid)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Encounter not found"})

    now = datetime.now(timezone.utc)
    # Push critical vitals
    vital = Vital(
        encounter_id=eid,
        spo2=88.0,
        heart_rate=136,
        respiratory_rate=32,
        bp_systolic=82,
        bp_diastolic=52,
        temperature=39.8,
        avpu=AVPU.PAIN,
        source=VitalSource.MANUAL,
        measured_at=now,
    )
    db.add(vital)

    await create_notification(
        db=db,
        notification_type="PRIORITY_CHANGED",
        message=f"DEMO: Patient deterioration simulated — {encounter.patient.display_id if encounter.patient else encounter_id}",
        encounter_id=eid,
        patient_display_id=encounter.patient.display_id if encounter.patient else None,
        is_urgent=True,
    )
    await db.flush()

    return {
        "message": "Deterioration simulated. Run /assessments/{id}/predict to see updated AI recommendation.",
        "encounter_id": encounter_id,
        "simulated_vitals": {
            "spo2": 88.0, "heart_rate": 136, "respiratory_rate": 32,
            "bp_systolic": 82, "bp_diastolic": 52, "temperature": 39.8, "avpu": "Pain"
        },
    }
