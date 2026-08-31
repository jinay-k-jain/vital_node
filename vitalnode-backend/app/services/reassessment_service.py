"""
Reassessment Service.
Handles creation of reassessment events and timer expiry notifications.
IMPORTANT: Timer expiry does NOT auto-change acuity. It notifies.
"""
from datetime import datetime, timezone
from typing import List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.encounter import Encounter, PatientStatus
from app.models.assessment import Assessment, AssessmentType
from app.services.audit_service import record_audit_event
from app.services.notification_service import create_notification
from app.core.logging import get_logger

logger = get_logger(__name__)


async def trigger_reassessment(
    db: AsyncSession,
    encounter: Encounter,
    triggered_by_user_id: uuid.UUID,
    triggered_by_staff_id: str,
    triggered_by_name: str,
    triggered_by_role: str,
) -> None:
    """
    Mark an encounter as due for reassessment.
    Increments reassessment count and logs audit event.
    Does NOT change acuity - that happens when the nurse submits new assessment.
    """
    encounter.reassessment_count = (encounter.reassessment_count or 0) + 1
    encounter.last_updated = datetime.now(timezone.utc)
    await db.flush()

    await record_audit_event(
        db=db,
        event_type="REASSESS_REQUESTED",
        user_id=triggered_by_user_id,
        user_staff_id=triggered_by_staff_id,
        user_name=triggered_by_name,
        user_role=triggered_by_role,
        patient_id=encounter.patient_id,
        patient_display_id=encounter.patient.display_id if encounter.patient else None,
        encounter_id=encounter.id,
    )


async def get_encounters_due_for_reassessment(
    db: AsyncSession,
) -> List[Encounter]:
    """Return all active encounters with an overdue reassessment timer."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Encounter)
        .options(selectinload(Encounter.patient))
        .where(
            Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]),
            Encounter.reassessment_due.isnot(None),
            Encounter.reassessment_due < now,
        )
    )
    return list(result.scalars().all())


async def check_and_notify_overdue(db: AsyncSession) -> int:
    """
    Check for overdue reassessments and create notifications.
    Returns the count of new notifications created.
    Called by a background worker or periodic health check.
    """
    overdue = await get_encounters_due_for_reassessment(db)
    count = 0
    for encounter in overdue:
        await create_notification(
            db=db,
            notification_type="REASSESSMENT_DUE",
            message=f"Reassessment overdue — {encounter.patient.display_id if encounter.patient else str(encounter.id)}",
            encounter_id=encounter.id,
            patient_display_id=encounter.patient.display_id if encounter.patient else None,
            is_urgent=True,
        )
        count += 1
    if count:
        logger.info("reassessment_overdue_notifications_sent", count=count)
    return count
