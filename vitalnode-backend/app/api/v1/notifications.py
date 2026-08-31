from app.api.v1.utils import ev
"""
Notifications API - /api/v1/notifications/*

GET  /api/v1/notifications           - list notifications
POST /api/v1/notifications/{id}/read - mark as read
POST /api/v1/notifications/read-all  - mark all as read
"""
from fastapi import APIRouter
from sqlalchemy import select
import uuid

from app.api.v1.deps import DbDep, CurrentUser
from app.services.notification_service import get_notifications, mark_read, mark_all_read

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="List notifications")
async def list_notifications(
    db: DbDep,
    current_user: CurrentUser,
    unread_only: bool = False,
    limit: int = 50,
):
    notifs = await get_notifications(db, user_id=current_user.id, unread_only=unread_only, limit=limit)
    return [
        {
            "id": str(n.id),
            "type": ev(n.type),
            "message": n.message,
            "patientId": str(n.encounter_id) if n.encounter_id else None,
            "patientDisplayId": n.patient_display_id,
            "timestamp": n.created_at.isoformat(),
            "read": n.is_read,
            "urgent": n.is_urgent,
        }
        for n in notifs
    ]


@router.post("/{notification_id}/read", summary="Mark notification as read")
async def read_one(notification_id: str, db: DbDep, current_user: CurrentUser):
    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        return {"error": "invalid id"}
    notif = await mark_read(db, nid)
    return {"id": notification_id, "read": notif.is_read if notif else False}


@router.post("/read-all", summary="Mark all notifications as read")
async def read_all(db: DbDep, current_user: CurrentUser):
    count = await mark_all_read(db, user_id=current_user.id)
    return {"marked_read": count}
