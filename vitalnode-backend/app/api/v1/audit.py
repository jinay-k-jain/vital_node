"""
Audit Log API - /api/v1/audit/*

GET /api/v1/audit - paginated audit log with filtering
"""
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, and_

from app.api.v1.deps import DbDep, CurrentUser
from app.models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", summary="Get audit log")
async def get_audit_log(
    db: DbDep,
    current_user: CurrentUser,
    event_type: Optional[str] = Query(None),
    patient_display_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    q = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).offset(offset)

    if event_type:
        q = q.where(AuditEvent.event_type == event_type.upper())

    if patient_display_id:
        q = q.where(AuditEvent.patient_display_id == patient_display_id)

    result = await db.execute(q)
    events = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "timestamp": e.timestamp.isoformat(),
            "patientId": str(e.patient_id) if e.patient_id else None,
            "patientDisplayId": e.patient_display_id,
            "eventType": e.event_type,
            "aiRecommendation": e.ai_recommendation,
            "aiConfidence": e.ai_confidence,
            "safetyFlag": e.safety_flag,
            "nurseAction": e.nurse_action,
            "finalAcuity": e.final_acuity,
            "overrideReason": e.override_reason,
            "modelVersion": e.model_version,
            "nurseId": str(e.user_id) if e.user_id else e.user_staff_id,
            "nurseName": e.user_name or "",
            "notes": e.notes,
        }
        for e in events
    ]
