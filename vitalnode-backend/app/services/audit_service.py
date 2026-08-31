"""
Audit service - insert-only audit event recording.
All clinical events, auth events, and system events flow through here.
Events are NEVER updated or deleted after creation.
"""
from datetime import datetime, timezone
from typing import Optional, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


async def record_audit_event(
    db: AsyncSession,
    event_type: str,
    user_id: Optional[uuid.UUID] = None,
    user_staff_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    patient_id: Optional[uuid.UUID] = None,
    patient_display_id: Optional[str] = None,
    encounter_id: Optional[uuid.UUID] = None,
    assessment_id: Optional[uuid.UUID] = None,
    ai_recommendation: Optional[str] = None,
    ai_confidence: Optional[float] = None,
    safety_flag: Optional[str] = None,
    nurse_action: Optional[str] = None,
    final_acuity: Optional[str] = None,
    override_reason: Optional[str] = None,
    model_version: Optional[str] = None,
    notes: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditEvent:
    """
    Record an immutable audit event.
    All parameters are optional except event_type to allow flexible usage.
    """
    event = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user_id,
        user_staff_id=user_staff_id,
        user_name=user_name,
        user_role=user_role,
        patient_id=patient_id,
        patient_display_id=patient_display_id,
        encounter_id=encounter_id,
        assessment_id=assessment_id,
        ai_recommendation=ai_recommendation,
        ai_confidence=ai_confidence,
        safety_flag=safety_flag,
        nurse_action=nurse_action,
        final_acuity=final_acuity,
        override_reason=override_reason,
        model_version=model_version,
        notes=notes,
        event_metadata=metadata,  # renamed: 'metadata' is reserved in SQLAlchemy
    )
    db.add(event)
    await db.flush()

    logger.info(
        "audit_event_recorded",
        event_type=event_type,
        user_staff_id=user_staff_id,
        patient_display_id=patient_display_id,
    )
    return event
