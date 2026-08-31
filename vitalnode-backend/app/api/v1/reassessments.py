"""
Reassessment API - /api/v1/reassessments/*
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.api.v1.utils import ev
from app.models.encounter import Encounter, PatientStatus
from app.services.reassessment_service import trigger_reassessment, get_encounters_due_for_reassessment

router = APIRouter(prefix="/reassessments", tags=["Reassessment"])


@router.get("", summary="Get encounters due for reassessment")
async def list_due(db: DbDep, current_user: CurrentUser):
    encounters = await get_encounters_due_for_reassessment(db)
    return [
        {
            "id": str(enc.id),
            "displayId": enc.patient.display_id if enc.patient else None,
            "currentAcuity": ev(enc.current_acuity),
            "safetyStatus": ev(enc.safety_status),
            "reassessmentDue": enc.reassessment_due.isoformat() if enc.reassessment_due else None,
            "reassessmentCount": enc.reassessment_count,
        }
        for enc in encounters
    ]


@router.post("/{encounter_id}", status_code=status.HTTP_200_OK,
             summary="Trigger reassessment for an encounter")
async def trigger(encounter_id: str, db: DbDep, current_user: NurseOrClinician):
    try:
        eid = uuid.UUID(encounter_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid encounter ID"})

    result = await db.execute(
        select(Encounter).options(selectinload(Encounter.patient)).where(Encounter.id == eid)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Encounter not found"})

    await trigger_reassessment(
        db=db, encounter=encounter,
        triggered_by_user_id=current_user.id,
        triggered_by_staff_id=current_user.staff_id,
        triggered_by_name=current_user.name,
        triggered_by_role=ev(current_user.role),
    )
    return {"message": "Reassessment triggered", "encounter_id": encounter_id}
