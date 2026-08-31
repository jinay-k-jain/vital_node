"""
System Info API - /api/v1/system/*

GET /api/v1/system/status   - admin-only detailed status
GET /api/v1/system/config   - hospital configuration (admin only)
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text, func, select

from app.api.v1.deps import DbDep, CurrentUser, AdminOnly
from app.core.config import get_settings
from app.models.encounter import Acuity, Encounter, PatientStatus
from app.models.audit import AuditEvent
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()


class ReassessmentIntervalsUpdate(BaseModel):
    critical: int = Field(ge=1, le=180)
    high: int = Field(ge=1, le=180)
    moderate: int = Field(ge=1, le=180)
    low: int = Field(ge=1, le=180)


@router.get("/status", summary="Detailed system status (admin only)")
async def system_status(db: DbDep, current_user: AdminOnly):
    """Full system health for the admin dashboard."""
    # DB check
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # Active patients
    count_result = await db.execute(
        select(func.count()).select_from(Encounter)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
    )
    active_patients = count_result.scalar()

    # Audit events today
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    audit_result = await db.execute(
        select(func.count()).select_from(AuditEvent).where(AuditEvent.timestamp >= today)
    )
    audit_today = audit_result.scalar()

    return {
        "database": "ok" if db_ok else "error",
        "ml_engine": settings.ml_engine,
        "ml_model_path": settings.model_path or "not configured",
        "voice_provider": settings.speech_provider,
        "demo_mode": settings.demo_mode,
        "environment": settings.app_env,
        "version": settings.app_version,
        "active_patients": active_patients,
        "audit_events_today": audit_today,
        "hospital": settings.hospital_name,
        "department": settings.hospital_department,
        "reassessment_intervals": {
            "CRITICAL": f"{settings.reassessment_critical_min} min",
            "HIGH": f"{settings.reassessment_high_min} min",
            "MODERATE": f"{settings.reassessment_moderate_min} min",
            "LOW": f"{settings.reassessment_low_min} min",
        },
    }


@router.get("/config", summary="Hospital configuration (admin only)")
async def hospital_config(current_user: AdminOnly):
    return {
        "hospital_name": settings.hospital_name,
        "department": settings.hospital_department,
        "location": settings.hospital_location,
        "reassessment_intervals": {
            "CRITICAL": settings.reassessment_critical_min,
            "HIGH": settings.reassessment_high_min,
            "MODERATE": settings.reassessment_moderate_min,
            "LOW": settings.reassessment_low_min,
        },
        "safety_thresholds": {
            "spo2_critical": 90,
            "spo2_warning": 95,
            "heart_rate_high": 120,
            "bp_systolic_low": 90,
            "respiratory_rate_high": 25,
            "temperature_high": 39.0,
            "min_confidence_auto_accept": 85,
            "data_completeness_warning": 70,
        },
        "routing": {
            "CRITICAL": "Resuscitation / Critical Care Area",
            "HIGH": "Urgent Care Area",
            "MODERATE": "Treatment Area",
            "LOW": "Waiting Area / Fast Track",
        },
        "model_version": "mock-v1.0" if settings.ml_engine == "mock" else "xgboost",
        "clinical_rule_version": "prototype-v1.0",
    }


@router.put("/reassessment-intervals", summary="Update reassessment intervals")
async def update_reassessment_intervals(
    payload: ReassessmentIntervalsUpdate, db: DbDep, current_user: CurrentUser,
):
    """Apply prototype timer settings and reschedule all active queue entries."""
    settings.reassessment_critical_min = payload.critical
    settings.reassessment_high_min = payload.high
    settings.reassessment_moderate_min = payload.moderate
    settings.reassessment_low_min = payload.low
    intervals = {
        Acuity.CRITICAL: payload.critical, Acuity.HIGH: payload.high,
        Acuity.MODERATE: payload.moderate, Acuity.LOW: payload.low,
    }
    now = datetime.now(timezone.utc)
    result = await db.execute(select(Encounter).where(
        Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]),
        Encounter.current_acuity.in_(list(intervals)),
    ))
    encounters = result.scalars().all()
    for encounter in encounters:
        encounter.reassessment_due = now + timedelta(minutes=intervals[encounter.current_acuity])
    await record_audit_event(
        db=db, event_type="CONFIG_CHANGED", user_id=current_user.id,
        user_staff_id=current_user.staff_id, user_name=current_user.name,
        user_role=current_user.role.value,
        metadata={"reassessment_intervals": payload.model_dump(), "rescheduled_encounters": len(encounters)},
    )
    await db.flush()
    return {"reassessment_intervals": payload.model_dump(), "rescheduled_encounters": len(encounters)}
