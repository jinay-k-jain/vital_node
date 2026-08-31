"""
WebSocket API - /api/v1/ws/queue
Broadcasts live queue updates to all connected frontend clients.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.utils import ev
from app.db.database import AsyncSessionLocal
from app.models.encounter import Encounter, PatientStatus, Acuity
from app.models.assessment import Assessment
from app.core.logging import get_logger

router = APIRouter(tags=["WebSocket"])
logger = get_logger(__name__)

_connected: Set[WebSocket] = set()


@router.websocket("/ws/queue")
async def queue_websocket(websocket: WebSocket):
    await websocket.accept()
    _connected.add(websocket)
    logger.info("websocket_client_connected", total=len(_connected))
    try:
        data = await _build_queue_payload()
        await websocket.send_text(json.dumps(data))
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected")
    finally:
        _connected.discard(websocket)


async def broadcast_queue_update():
    if not _connected:
        return
    try:
        data = await _build_queue_payload()
        payload = json.dumps(data)
        dead = set()
        for ws in list(_connected):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        _connected.difference_update(dead)
    except Exception as exc:
        logger.error("websocket_broadcast_failed", error=str(exc))


async def _build_queue_payload() -> dict:
    now = datetime.now(timezone.utc)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Encounter)
                .options(
                    selectinload(Encounter.patient),
                    selectinload(Encounter.vitals),
                    selectinload(Encounter.assessments).selectinload(Assessment.ai_recommendation),
                )
                .where(
                    Encounter.status.in_([PatientStatus.WAITING, PatientStatus.IN_PROGRESS]),
                    Encounter.current_acuity != Acuity.PENDING,
                )
                .order_by(Encounter.current_acuity)
            )
            encounters = result.scalars().all()

            queue = []
            for enc in encounters:
                p = enc.patient
                if not p:
                    continue

                latest_vital = None
                if enc.vitals:
                    latest_vital = sorted(enc.vitals, key=lambda v: v.measured_at, reverse=True)[0]

                latest_rec = None
                if enc.assessments:
                    latest_asmt = sorted(enc.assessments, key=lambda a: a.created_at, reverse=True)[0]
                    latest_rec = getattr(latest_asmt, 'ai_recommendation', None)

                at = enc.arrival_time
                if at and at.tzinfo is None:
                    at = at.replace(tzinfo=timezone.utc)
                waiting_seconds = int((now - at).total_seconds()) if at else 0

                queue.append({
                    "id": str(enc.id),
                    "displayId": p.display_id,
                    "name": p.name,
                    "age": p.age,
                    "sex": ev(p.sex),
                    "ageGroup": ev(p.age_group),
                    "arrivalMode": ev(enc.arrival_mode),
                    "arrivalTime": enc.arrival_time.isoformat() if enc.arrival_time else None,
                    "currentAcuity": ev(enc.current_acuity),
                    "safetyStatus": ev(enc.safety_status),
                    "status": ev(enc.status),
                    "waitingTime": waiting_seconds,
                    "reassessmentDue": enc.reassessment_due.isoformat() if enc.reassessment_due else None,
                    "reassessmentCount": enc.reassessment_count,
                    "chiefComplaint": (latest_asmt.confirmed_complaint or latest_asmt.chief_complaint) if enc.assessments else "",
                    "symptoms": latest_asmt.symptoms or [] if enc.assessments else [],
                    "dangerSigns": latest_asmt.danger_signs or [] if enc.assessments else [],
                    "lastUpdated": enc.last_updated.isoformat() if enc.last_updated else None,
                    "_assessmentId": str(latest_asmt.id) if enc.assessments else None,
                    "confidence": latest_rec.confidence if latest_rec else None,
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
                    } if latest_vital else None,
                })

            return {"type": "QUEUE_UPDATE", "timestamp": now.isoformat(), "queue": queue, "total": len(queue)}
    except Exception as exc:
        logger.error("queue_payload_build_failed", error=str(exc))
        return {"type": "QUEUE_UPDATE", "timestamp": now.isoformat(), "queue": [], "total": 0}
