from app.api.v1.utils import ev
"""
Surge Mode API - /api/v1/surge/*

POST /api/v1/surge/start  - activate 3× surge simulation
POST /api/v1/surge/stop   - deactivate surge
GET  /api/v1/surge/status - current surge status
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import select, func, update

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.models.encounter import Encounter, PatientStatus
from app.services.audit_service import record_audit_event
from app.services.surge_service import create_surge_patients

router = APIRouter(prefix="/surge", tags=["Surge Mode"])
# In-memory surge state (suitable for prototype; use Redis/DB for production)
_surge_active: bool = False
_surge_start_time: datetime | None = None


@router.post("/start", summary="Activate surge mode simulation")
async def start_surge(db: DbDep, current_user: NurseOrClinician):
    global _surge_active, _surge_start_time
    if _surge_active:
        return {"active": True, "message": "Surge mode is already active."}

    normal_count = await db.scalar(
        select(func.count()).select_from(Encounter)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
        .where(Encounter.is_surge_patient == False)
    ) or 0
    additional_count = normal_count * 2
    created = await create_surge_patients(db, current_user, additional_count)
    _surge_active = True
    _surge_start_time = datetime.now(timezone.utc)

    await record_audit_event(
        db=db,
        event_type="SURGE_STARTED",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
        metadata={"normal_patient_count": normal_count, "surge_patient_count": created, "target_patient_count": normal_count * 3},
    )

    return {
        "active": True,
        "normal_patient_count": normal_count,
        "surge_patient_count": created,
        "target_patient_count": normal_count * 3,
        "message": f"Surge mode activated. {normal_count} normal patients + {created} synthetic arrivals = {normal_count * 3} patients (3× volume).",
        "started_at": _surge_start_time.isoformat(),
    }


@router.post("/stop", summary="Deactivate surge mode simulation")
async def stop_surge(db: DbDep, current_user: NurseOrClinician):
    global _surge_active, _surge_start_time

    await record_audit_event(
        db=db,
        event_type="SURGE_STOPPED",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
    )

    await db.execute(
        update(Encounter)
        .where(Encounter.is_surge_patient == True)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
        .values(status=PatientStatus.DISCHARGED)
    )
    _surge_active = False
    _surge_start_time = None
    return {"active": False, "message": "Surge mode deactivated"}


@router.get("/status", summary="Get current surge status")
async def surge_status(db: DbDep, current_user: CurrentUser):
    total_result = await db.execute(
        select(func.count()).select_from(Encounter)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
    )
    total = total_result.scalar()
    surge_count = await db.scalar(
        select(func.count()).select_from(Encounter)
        .where(Encounter.is_surge_patient == True)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
    ) or 0

    return {
        "active": _surge_active,
        "started_at": _surge_start_time.isoformat() if _surge_start_time else None,
        "current_patient_count": total,
        "surge_patient_count": surge_count,
        "message": "3× volume simulation active" if _surge_active else "Normal operation",
    }
