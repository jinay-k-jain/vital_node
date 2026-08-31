"""
Queue API - /api/v1/queue/*
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
import uuid
from sqlalchemy import select, func

from app.api.v1.deps import DbDep, CurrentUser
from app.api.v1.utils import ev
from app.models.encounter import Encounter, PatientStatus, Acuity, SafetyStatus
from app.services.queue_service import get_queue

router = APIRouter(prefix="/queue", tags=["Queue"])


@router.get("", summary="Get ordered patient queue")
async def queue(
    db: DbDep, current_user: CurrentUser,
    acuity: Optional[str] = Query(None),
    safety_flags: bool = Query(False),
    limit: int = Query(100, le=500),
):
    encounters = await get_queue(
        db, acuity_filter=acuity,
        safety_filter=safety_flags if safety_flags else None,
        limit=limit,
    )

    now = datetime.now(timezone.utc)
    results = []
    for enc in encounters:
        p = enc.patient
        if not p:
            continue

        latest_assessment = None
        latest_rec = None
        if enc.assessments:
            latest_assessment = sorted(enc.assessments, key=lambda a: a.created_at, reverse=True)[0]
            if hasattr(latest_assessment, 'ai_recommendation') and latest_assessment.ai_recommendation:
                r = latest_assessment.ai_recommendation
                esi_map = {"CRITICAL": 1, "HIGH": 2, "MODERATE": 3, "LOW": 4, "PENDING": 0}
                acuity_str = ev(r.acuity)
                latest_rec = {
                    "acuity": acuity_str,
                    "esiLevel": esi_map.get(acuity_str, 3),
                    "confidence": r.confidence,
                    "safetyStatus": ev(r.safety_status),
                    "safetyFlag": r.safety_flag,
                    "dataCompleteness": r.data_completeness,
                    "keyReasons": r.key_reasons or [],
                    "clinicalRules": r.clinical_rules or [],
                    "topFactors": r.top_factors or [],
                    "modelVersion": r.model_version,
                    "timestamp": r.recommended_at.isoformat(),
                    "isConservative": r.is_conservative,
                }

        latest_vital = None
        if enc.vitals:
            latest_vital = sorted(enc.vitals, key=lambda v: v.measured_at, reverse=True)[0]

        at = enc.arrival_time
        if at and at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        waiting_seconds = int((now - at).total_seconds()) if at else 0

        results.append({
            "id": str(enc.id),
            "displayId": p.display_id,
            "name": p.name,
            "age": p.age,
            "sex": ev(p.sex),
            "ageGroup": ev(p.age_group),
            "arrivalMode": ev(enc.arrival_mode),
            "arrivalTime": enc.arrival_time.isoformat() if enc.arrival_time else None,
            "isPregnant": enc.is_pregnant,
            "currentAcuity": ev(enc.current_acuity),
            "safetyStatus": ev(enc.safety_status),
            "status": ev(enc.status),
            "waitingTime": waiting_seconds,
            "reassessmentDue": enc.reassessment_due.isoformat() if enc.reassessment_due else None,
            "reassessmentCount": enc.reassessment_count,
            "chiefComplaint": (latest_assessment.confirmed_complaint or latest_assessment.chief_complaint) if latest_assessment else "",
            "symptoms": latest_assessment.symptoms or [] if latest_assessment else [],
            "dangerSigns": latest_assessment.danger_signs or [] if latest_assessment else [],
            "history": {
                "available": ev(latest_assessment.history_status) == "AVAILABLE" if latest_assessment else False,
                "conditions": latest_assessment.history_conditions or [] if latest_assessment else [],
                "medications": latest_assessment.history_medications or [] if latest_assessment else [],
                "allergies": latest_assessment.history_allergies or [] if latest_assessment else [],
            },
            "deviceConnected": enc.device_connected,
            "isSimulation": p.is_simulation,
            "lastUpdated": enc.last_updated.isoformat() if enc.last_updated else None,
            "aiRecommendation": latest_rec,
            "nurseDecision": None,
            "_assessmentId": str(latest_assessment.id) if latest_assessment else None,
            "vitals": {
                "spo2": latest_vital.spo2,
                "heartRate": latest_vital.heart_rate,
                "respiratoryRate": latest_vital.respiratory_rate,
                "bpSystolic": latest_vital.bp_systolic,
                "bpDiastolic": latest_vital.bp_diastolic,
                "temperature": latest_vital.temperature,
                "avpu": ev(latest_vital.avpu) if latest_vital.avpu else None,
                "timestamp": latest_vital.measured_at.isoformat() if latest_vital.measured_at else None,
                "source": ev(latest_vital.source),
            } if latest_vital else {"timestamp": now.isoformat(), "source": "Manual Entry"},
        })

    return results


@router.post("/{encounter_id}/complete", status_code=204, summary="Mark patient as bed assigned")
async def complete_queue_entry(encounter_id: str, db: DbDep, current_user: CurrentUser):
    try:
        encounter_uuid = uuid.UUID(encounter_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid encounter ID") from exc
    result = await db.execute(select(Encounter).where(Encounter.id == encounter_uuid))
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    encounter.status = PatientStatus.ADMITTED
    encounter.last_updated = datetime.now(timezone.utc)
    await db.flush()


@router.get("/summary", summary="Department summary statistics")
async def summary(db: DbDep, current_user: CurrentUser):
    active = [PatientStatus.WAITING, PatientStatus.IN_PROGRESS]
    now = datetime.now(timezone.utc)

    total    = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active)))).scalar()
    critical = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.current_acuity == Acuity.CRITICAL))).scalar()
    high     = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.current_acuity == Acuity.HIGH))).scalar()
    moderate = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.current_acuity == Acuity.MODERATE))).scalar()
    low      = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.current_acuity == Acuity.LOW))).scalar()
    safety_v = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.safety_status.in_([SafetyStatus.VERIFY, SafetyStatus.URGENT_REVIEW])))).scalar()
    overdue  = (await db.execute(select(func.count()).select_from(Encounter).where(Encounter.status.in_(active), Encounter.reassessment_due.isnot(None), Encounter.reassessment_due < now))).scalar()

    return {
        "critical": critical, "high": high, "moderate": moderate, "low": low,
        "waiting": total, "dueForReassessment": overdue,
        "safetyVerificationRequired": safety_v, "totalPatients": total,
    }
