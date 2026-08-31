from app.api.v1.utils import ev
"""
Device Simulation API - /api/v1/devices/*

Real medical devices never connect directly to the frontend.
This gateway sits between the device and the clinical pipeline.

POST /api/v1/devices/register              - register a simulated device
GET  /api/v1/devices                       - list devices
GET  /api/v1/devices/{device_id}           - get device status
POST /api/v1/devices/{device_id}/simulate  - simulate a vital reading
POST /api/v1/devices/{device_id}/disconnect - simulate disconnect
"""
import uuid
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.models.device import Device, DeviceStatus
from app.models.encounter import Encounter
from app.models.vital import Vital, VitalSource, AVPU
from app.services.audit_service import record_audit_event
from app.services.notification_service import create_notification
from app.core.logging import get_logger

router = APIRouter(prefix="/devices", tags=["Device Simulation"])
logger = get_logger(__name__)


class DeviceRegisterRequest(BaseModel):
    device_code: str
    device_name: str
    encounter_id: Optional[str] = None


class SimulateVitalRequest(BaseModel):
    scenario: str = "normal"  # normal | worsening | critical | disconnect
    encounter_id: Optional[str] = None


@router.post("/register", summary="Register a simulated device")
async def register_device(payload: DeviceRegisterRequest, db: DbDep, current_user: NurseOrClinician):
    # Check duplicate
    existing = await db.execute(select(Device).where(Device.device_code == payload.device_code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Device '{payload.device_code}' already registered"},
        )

    enc_id = None
    if payload.encounter_id:
        try:
            enc_id = uuid.UUID(payload.encounter_id)
        except ValueError:
            pass

    device = Device(
        device_code=payload.device_code,
        device_name=payload.device_name,
        status=DeviceStatus.SIMULATED,
        encounter_id=enc_id,
        last_sync=datetime.now(timezone.utc),
        is_simulated=True,
    )
    db.add(device)
    await db.flush()

    await record_audit_event(
        db=db,
        event_type="DEVICE_EVENT",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
        metadata={"action": "DEVICE_REGISTERED", "device_code": payload.device_code},
    )

    return {"device_id": str(device.id), "device_code": device.device_code, "status": ev(device.status)}


@router.get("", summary="List all devices")
async def list_devices(db: DbDep, current_user: CurrentUser):
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "device_code": d.device_code,
            "device_name": d.device_name,
            "status": ev(d.status),
            "encounter_id": str(d.encounter_id) if d.encounter_id else None,
            "last_sync": d.last_sync.isoformat() if d.last_sync else None,
            "is_simulated": d.is_simulated,
        }
        for d in devices
    ]


@router.get("/{device_id}", summary="Get device status")
async def get_device(device_id: str, db: DbDep, current_user: CurrentUser):
    try:
        did = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid device ID"})

    result = await db.execute(select(Device).where(Device.id == did))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Device not found"})

    return {
        "id": str(device.id),
        "device_code": device.device_code,
        "status": ev(device.status),
        "last_sync": device.last_sync.isoformat() if device.last_sync else None,
    }


@router.post("/{device_id}/simulate", summary="Simulate a vital reading from device")
async def simulate_vital(
    device_id: str,
    payload: SimulateVitalRequest,
    db: DbDep,
    current_user: NurseOrClinician,
):
    """
    Simulate a device pushing vitals into the pipeline.
    Scenarios: normal | worsening | critical
    """
    try:
        did = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid device ID"})

    result = await db.execute(select(Device).where(Device.id == did))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Device not found"})

    # Determine which encounter to attach vitals to
    encounter_id_str = payload.encounter_id or (str(device.encounter_id) if device.encounter_id else None)
    if not encounter_id_str:
        raise HTTPException(
            status_code=400,
            detail={"code": "NO_ENCOUNTER", "message": "Device is not assigned to an encounter. Pass encounter_id."},
        )

    enc_id = uuid.UUID(encounter_id_str)
    enc_result = await db.execute(select(Encounter).where(Encounter.id == enc_id))
    encounter = enc_result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Encounter not found"})

    # Generate vitals based on scenario
    vitals = _generate_scenario_vitals(payload.scenario)
    now = datetime.now(timezone.utc)

    vital = Vital(
        encounter_id=enc_id,
        device_id=did,
        spo2=vitals["spo2"],
        heart_rate=vitals["heart_rate"],
        respiratory_rate=vitals["respiratory_rate"],
        bp_systolic=vitals["bp_systolic"],
        bp_diastolic=vitals["bp_diastolic"],
        temperature=vitals["temperature"],
        avpu=AVPU(vitals["avpu"]),
        source=VitalSource.DEVICE,
        measured_at=now,
    )
    db.add(vital)

    # Update device last sync
    device.last_sync = now
    device.status = DeviceStatus.CONNECTED
    encounter.device_connected = True
    await db.flush()

    await record_audit_event(
        db=db,
        event_type="VITAL_UPDATED",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
        encounter_id=enc_id,
        metadata={"device_code": device.device_code, "scenario": payload.scenario},
    )

    # Notify if worsening/critical
    if payload.scenario in ("worsening", "critical"):
        await create_notification(
            db=db,
            notification_type="VITAL_RECEIVED",
            message=f"Device vital update — {payload.scenario.upper()} reading received",
            encounter_id=enc_id,
            is_urgent=payload.scenario == "critical",
        )

    return {"message": "Vital simulated", "scenario": payload.scenario, "vitals": vitals}


@router.post("/{device_id}/disconnect", summary="Simulate device disconnect")
async def disconnect_device(device_id: str, db: DbDep, current_user: NurseOrClinician):
    try:
        did = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "Invalid device ID"})

    result = await db.execute(select(Device).where(Device.id == did))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Device not found"})

    device.status = DeviceStatus.DISCONNECTED

    if device.encounter_id:
        enc_result = await db.execute(select(Encounter).where(Encounter.id == device.encounter_id))
        enc = enc_result.scalar_one_or_none()
        if enc:
            enc.device_connected = False
            await create_notification(
                db=db,
                notification_type="DEVICE_DISCONNECTED",
                message=f"Device {device.device_code} disconnected — manual entry required",
                encounter_id=device.encounter_id,
                is_urgent=False,
            )

    await db.flush()

    await record_audit_event(
        db=db,
        event_type="DEVICE_EVENT",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=ev(current_user.role),
        metadata={"action": "DEVICE_DISCONNECTED", "device_code": device.device_code},
    )

    return {"message": "Device disconnected. Manual vital entry is now available."}


def _generate_scenario_vitals(scenario: str) -> dict:
    """Generate plausible vital values for a given scenario."""
    if scenario == "normal":
        return {
            "spo2": round(random.uniform(96, 99), 1),
            "heart_rate": random.randint(65, 90),
            "respiratory_rate": random.randint(14, 18),
            "bp_systolic": random.randint(110, 130),
            "bp_diastolic": random.randint(70, 85),
            "temperature": round(random.uniform(36.5, 37.2), 1),
            "avpu": "Alert",
        }
    elif scenario == "worsening":
        return {
            "spo2": round(random.uniform(91, 94), 1),
            "heart_rate": random.randint(105, 125),
            "respiratory_rate": random.randint(22, 28),
            "bp_systolic": random.randint(90, 105),
            "bp_diastolic": random.randint(60, 72),
            "temperature": round(random.uniform(37.8, 39.0), 1),
            "avpu": "Voice",
        }
    elif scenario == "critical":
        return {
            "spo2": round(random.uniform(84, 89), 1),
            "heart_rate": random.randint(130, 150),
            "respiratory_rate": random.randint(28, 36),
            "bp_systolic": random.randint(75, 88),
            "bp_diastolic": random.randint(45, 58),
            "temperature": round(random.uniform(39.5, 41.0), 1),
            "avpu": "Pain",
        }
    # Default to normal
    return _generate_scenario_vitals("normal")
