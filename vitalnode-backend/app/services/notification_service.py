"""
Notification Service.
Creates and retrieves in-app notifications.
"""
from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_notification(
    db: AsyncSession,
    notification_type: str,
    message: str,
    encounter_id: Optional[uuid.UUID] = None,
    patient_display_id: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    is_urgent: bool = False,
) -> Notification:
    notif = Notification(
        type=NotificationType(notification_type),
        message=message,
        encounter_id=encounter_id,
        patient_display_id=patient_display_id,
        user_id=user_id,
        is_urgent=is_urgent,
        is_read=False,
    )
    db.add(notif)
    await db.flush()
    return notif


async def get_notifications(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    unread_only: bool = False,
    limit: int = 50,
) -> List[Notification]:
    q = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(Notification.is_read == False)
    if user_id:
        from sqlalchemy import or_
        q = q.where(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, notification_id: uuid.UUID) -> Optional[Notification]:
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
        await db.flush()
    return notif


async def mark_all_read(db: AsyncSession, user_id: Optional[uuid.UUID] = None) -> int:
    q = select(Notification).where(Notification.is_read == False)
    if user_id:
        from sqlalchemy import or_
        q = q.where(or_(Notification.user_id == user_id, Notification.user_id.is_(None)))
    result = await db.execute(q)
    notifs = result.scalars().all()
    for n in notifs:
        n.is_read = True
    await db.flush()
    return len(list(notifs))
