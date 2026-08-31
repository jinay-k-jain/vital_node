"""
Patients API - /api/v1/patients/*
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.api.v1.utils import ev
from app.models.patient import Patient
from app.models.encounter import Encounter
from app.models.assessment import Assessment
from app.models.audit import AuditEvent
from app.schemas.assessment import AssessmentCreate
from app.services.patient_service import create_patient_and_encounter, search_patients
from app.services.assessment_service import run_ai_assessment
from app.services.audit_service import record_audit_event
from app.core.logging import get_logger

router = APIRouter(prefix="/patients", tags=["Patients"])
logger = get_logger(__name__)


@router.post("/assess", status_code=status.HTTP_201_CREATED,
             summary="Create patient + encounter + run AI assessment")
async def create_assessment(payload: AssessmentCreate, db: DbDep, current_user: NurseOrClinician):
    try:
        patient, encounter, assessment = await create_patient_and_encounter(
            db=db, payload=payload, submitted_by_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc

    # Reload with all relations in same session to avoid detached-instance errors
    # Done AFTER assessment creation so vitals are included
    result = await db.execute(
        select(Encounter)
        .options(
            selectinload(Encounter.patient),
            selectinload(Encounter.vitals),
            selectinload(Encounter.assessments),
        )
        .where(Encounter.id == encounter.id)
    )
    encounter = result.scalar_one()

    # Get the assessment we just created (last one)
    assessment = sorted(encounter.assessments, key=lambda a: a.created_at, reverse=True)[0] if encounter.assessments else assessment

    recommendation = await run_ai_assessment(
        db=db, assessment=assessment, encounter=encounter,
        submitted_by_user_id=current_user.id,
        submitted_by_staff_id=current_user.staff_id,
        submitted_by_name=current_user.name,
        submitted_by_role=ev(current_user.role),
    )

    await record_audit_event(
        db=db, event_type="PATIENT_CREATED",
        user_id=current_user.id, user_staff_id=current_user.staff_id,
        user_name=current_user.name, user_role=ev(current_user.role),
        patient_id=patient.id, patient_display_id=patient.display_id,
        encounter_id=encounter.id,
    )

    resp = _build_response(patient, encounter, assessment, recommendation, None)
    # Show the AI recommendation in the review screen without implying it has
    # already been accepted as the encounter's queue acuity.
    if not payload.reassessment_encounter_id:
        resp["currentAcuity"] = "PENDING"
    # Include assessment ID so frontend can call /assessments/{id}/decision
    resp["_assessmentId"] = str(assessment.id)
    return resp


@router.get("/search", summary="Search patients by name or patient ID")
async def search(q: str = Query(..., min_length=1), db: DbDep = ..., current_user: CurrentUser = ...):
    patients = await search_patients(db, q)
    results = []
    for p in patients:
        enc_result = await db.execute(
            select(Encounter).where(Encounter.patient_id == p.id)
            .order_by(desc(Encounter.arrival_time)).limit(1)
        )
        enc = enc_result.scalar_one_or_none()
        results.append({
            "id": str(p.id),
            "displayId": p.display_id,
            "name": p.name,
            "age": p.age,
            "sex": ev(p.sex),
            "ageGroup": ev(p.age_group),
            "chiefComplaint": None,
            "currentAcuity": ev(enc.current_acuity) if enc else "PENDING",
            "status": ev(enc.status) if enc else "WAITING",
        })
    return results


@router.get("/{patient_id}/timeline", summary="Patient event timeline")
async def get_timeline(patient_id: str, db: DbDep, current_user: CurrentUser):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.patient_display_id == patient_id)
        .order_by(AuditEvent.timestamp.asc())
    )
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "timestamp": e.timestamp.isoformat(),
            "type": e.event_type,
            "title": _event_title(e.event_type),
            "description": _event_description(e),
            "acuity": e.final_acuity or e.ai_recommendation,
            "confidence": e.ai_confidence,
        }
        for e in events
    ]


def _event_title(event_type: str) -> str:
    return {
        "ARRIVAL": "Patient arrived", "PATIENT_CREATED": "Patient registered",
        "AI_PREDICTION": "AI assessment completed", "ACCEPTED": "AI recommendation accepted",
        "OVERRIDE": "Nurse override", "REASSESS_REQUESTED": "Reassessment requested",
        "VITAL_UPDATED": "Vital signs updated",
    }.get(event_type, event_type.replace("_", " ").title())


def _event_description(event: AuditEvent) -> str:
    parts = []
    if event.user_name: parts.append(f"By: {event.user_name}")
    if event.ai_recommendation: parts.append(f"AI: {event.ai_recommendation}")
    if event.final_acuity and event.final_acuity != event.ai_recommendation:
        parts.append(f"Final: {event.final_acuity}")
    if event.override_reason: parts.append(f"Reason: {event.override_reason}")
    return " · ".join(parts) if parts else event.event_type


def _build_response(patient, encounter, assessment, recommendation, nurse_decision):
    """Build frontend-compatible patient shape. Uses ev() for all enum fields."""
    latest_vital = None
    if encounter.vitals:
        latest_vital = sorted(encounter.vitals, key=lambda v: v.measured_at, reverse=True)[0]

    vitals = {}
    if latest_vital:
        vitals = {
            "spo2": latest_vital.spo2,
            "heartRate": latest_vital.heart_rate,
            "respiratoryRate": latest_vital.respiratory_rate,
            "bpSystolic": latest_vital.bp_systolic,
            "bpDiastolic": latest_vital.bp_diastolic,
            "temperature": latest_vital.temperature,
            "avpu": ev(latest_vital.avpu) if latest_vital.avpu else None,
            "timestamp": latest_vital.measured_at.isoformat(),
            "source": ev(latest_vital.source),
        }

    history = {
        "available": ev(assessment.history_status) == "AVAILABLE",
        "conditions": assessment.history_conditions or [],
        "medications": assessment.history_medications or [],
        "allergies": assessment.history_allergies or [],
        "notes": assessment.history_notes,
    }

    ai_rec = None
    if recommendation:
        acuity_str = ev(recommendation.acuity)
        # Map acuity → ESI level for frontend display
        esi_map = {"CRITICAL": 1, "HIGH": 2, "MODERATE": 3, "LOW": 4, "PENDING": 0}
        esi_level = esi_map.get(acuity_str, 3)
        ai_rec = {
            "acuity": acuity_str,
            "esiLevel": esi_level,
            "confidence": recommendation.confidence,
            "safetyStatus": ev(recommendation.safety_status),
            "safetyFlag": recommendation.safety_flag,
            "dataCompleteness": recommendation.data_completeness,
            "keyReasons": recommendation.key_reasons or [],
            "clinicalRules": recommendation.clinical_rules or [],
            "topFactors": recommendation.top_factors or [],
            "modelVersion": recommendation.model_version,
            "timestamp": recommendation.recommended_at.isoformat(),
            "isConservative": recommendation.is_conservative,
        }

    nd = None
    if nurse_decision:
        nd = {
            "action": nurse_decision.action,
            "finalAcuity": ev(nurse_decision.final_acuity),
            "overrideReason": nurse_decision.override_reason,
            "overrideNote": nurse_decision.override_note,
            "nurseId": str(nurse_decision.nurse_id) if nurse_decision.nurse_id else "",
            "nurseName": "",
            "timestamp": nurse_decision.decided_at.isoformat(),
        }

    now = datetime.now(timezone.utc)
    waiting_seconds = 0
    if encounter.arrival_time:
        at = encounter.arrival_time
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        waiting_seconds = int((now - at).total_seconds())

    return {
        "id": str(encounter.id),
        "displayId": patient.display_id,
        "name": patient.name,
        "age": patient.age,
        "sex": ev(patient.sex),
        "ageGroup": ev(patient.age_group),
        "arrivalMode": ev(encounter.arrival_mode),
        "arrivalTime": encounter.arrival_time.isoformat(),
        "isPregnant": encounter.is_pregnant,
        "chiefComplaint": assessment.confirmed_complaint or assessment.chief_complaint or "",
        "symptoms": assessment.symptoms or [],
        "dangerSigns": assessment.danger_signs or [],
        "vitals": vitals,
        "history": history,
        "currentAcuity": ev(encounter.current_acuity),
        "aiRecommendation": ai_rec,
        "safetyStatus": ev(encounter.safety_status),
        "status": ev(encounter.status),
        "waitingTime": waiting_seconds,
        "reassessmentDue": encounter.reassessment_due.isoformat() if encounter.reassessment_due else None,
        "reassessmentCount": encounter.reassessment_count,
        "lastUpdated": encounter.last_updated.isoformat(),
        "nurseDecision": nd,
        "isSimulation": patient.is_simulation,
        "deviceConnected": encounter.device_connected,
    }
