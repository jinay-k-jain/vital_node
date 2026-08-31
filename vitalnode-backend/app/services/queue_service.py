"""
Queue Service.
Returns the ordered patient queue.
Priority is deterministic and computed server-side - never by the frontend.

Priority formula (lower score = higher priority):
  acuity_rank * 1000 - safety_bonus - overdue_bonus - waiting_bonus
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.encounter import Encounter, PatientStatus, Acuity, SafetyStatus
from app.models.queue_entry import QueueEntry
from app.models.patient import Patient
from app.models.assessment import Assessment
from app.models.recommendation import AIRecommendation, NurseDecision
from app.models.vital import Vital


async def get_queue(
    db: AsyncSession,
    acuity_filter: Optional[str] = None,
    safety_filter: Optional[bool] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
) -> List[Encounter]:
    """
    Return encounters in priority order.
    Optionally filtered by acuity, safety status, and patient status.
    """
    q = (
        select(Encounter)
        .join(QueueEntry, QueueEntry.encounter_id == Encounter.id)
        .options(
            selectinload(Encounter.patient),
            selectinload(Encounter.vitals),
            selectinload(Encounter.assessments)
            .selectinload(Assessment.ai_recommendation),
            selectinload(Encounter.assessments)
            .selectinload(Assessment.nurse_decision),
        )
        .where(
            Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]),
            # An AI recommendation must be explicitly accepted or overridden
            # before the patient can enter the live queue.
            Encounter.current_acuity != Acuity.PENDING,
        )
        .order_by(QueueEntry.priority_score.asc())
        .limit(limit)
    )

    if acuity_filter:
        q = q.where(Encounter.current_acuity == Acuity(acuity_filter))

    if safety_filter:
        q = q.where(
            Encounter.safety_status.in_([SafetyStatus.VERIFY, SafetyStatus.URGENT_REVIEW])
        )

    result = await db.execute(q)
    return list(result.scalars().all())


async def get_surge_queue(db: AsyncSession) -> List[Encounter]:
    """Return surge encounters only."""
    result = await db.execute(
        select(Encounter)
        .options(selectinload(Encounter.patient))
        .where(Encounter.is_surge_patient == True)
        .where(Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]))
    )
    return list(result.scalars().all())
