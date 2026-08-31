"""
Assessments API - /api/v1/assessments/*
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.api.v1.utils import ev
from app.models.assessment import Assessment
from app.models.encounter import Encounter
from app.schemas.assessment import NurseDecisionCreate
from app.services.assessment_service import run_ai_assessment, record_nurse_decision
from app.services.data_quality_service import compute_data_quality
from app.services.vital_service import get_latest_vital
from app.services.notification_service import create_notification
from app.core.logging import get_logger

router = APIRouter(prefix="/assessments", tags=["Assessments"])
logger = get_logger(__name__)


async def _get_assessment_and_encounter(db, assessment_id: str):
    try:
        aid = uuid.UUID(assessment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid assessment ID"})

    result = await db.execute(
        select(Assessment)
        .options(
            selectinload(Assessment.encounter).selectinload(Encounter.patient),
            selectinload(Assessment.encounter).selectinload(Encounter.vitals),
            selectinload(Assessment.ai_recommendation),
            selectinload(Assessment.nurse_decision),
        )
        .where(Assessment.id == aid)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Assessment not found"})
    return assessment


@router.post("/{assessment_id}/predict", summary="Re-run AI prediction pipeline")
async def predict(assessment_id: str, db: DbDep, current_user: NurseOrClinician):
    assessment = await _get_assessment_and_encounter(db, assessment_id)
    recommendation = await run_ai_assessment(
        db=db, assessment=assessment, encounter=assessment.encounter,
        submitted_by_user_id=current_user.id,
        submitted_by_staff_id=current_user.staff_id,
        submitted_by_name=current_user.name,
        submitted_by_role=ev(current_user.role),
    )
    return {
        "assessment_id": assessment_id,
        "recommendation": {
            "acuity": ev(recommendation.acuity),
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
    }


@router.post("/{assessment_id}/decision", summary="Record nurse decision")
async def nurse_decision(
    assessment_id: str, payload: NurseDecisionCreate,
    db: DbDep, current_user: NurseOrClinician,
):
    assessment = await _get_assessment_and_encounter(db, assessment_id)
    encounter = assessment.encounter

    decision = await record_nurse_decision(
        db=db, assessment=assessment, encounter=encounter, decision=payload,
        nurse_user_id=current_user.id, nurse_staff_id=current_user.staff_id,
        nurse_name=current_user.name, nurse_role=ev(current_user.role),
    )

    if payload.action == "OVERRIDE":
        await create_notification(
            db=db, notification_type="PRIORITY_CHANGED",
            message=f"Priority updated to {payload.final_acuity} — {encounter.patient.display_id if encounter.patient else ''}",
            encounter_id=encounter.id,
            patient_display_id=encounter.patient.display_id if encounter.patient else None,
            is_urgent=payload.final_acuity in ("CRITICAL", "HIGH"),
        )

    return {
        "decision_id": str(decision.id),
        "action": decision.action,
        "final_acuity": ev(decision.final_acuity),
        "decided_at": decision.decided_at.isoformat(),
    }


@router.get("/{assessment_id}/quality", summary="Get data quality report")
async def data_quality(assessment_id: str, db: DbDep, current_user: CurrentUser):
    assessment = await _get_assessment_and_encounter(db, assessment_id)
    latest_vital = await get_latest_vital(db, assessment.encounter.id)
    return compute_data_quality(assessment, latest_vital)
