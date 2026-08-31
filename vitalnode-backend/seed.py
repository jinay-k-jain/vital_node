"""
VitalNode Seed Script
=====================
Creates demo users and 20+ synthetic patients that mirror the mockPatients.ts data.

Run:
    python seed.py

Requirements:
    - PostgreSQL running
    - .env configured with DATABASE_SYNC_URL
    - Alembic migrations already applied: alembic upgrade head

All data is clearly marked is_simulation=True.
Never use real patient data.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.patient import Patient, AgeGroup
from app.models.encounter import (
    Encounter, ArrivalMode, PatientStatus, Acuity, SafetyStatus
)
from app.models.assessment import Assessment, AssessmentType, HistoryStatus
from app.models.vital import Vital, VitalSource, AVPU
from app.models.recommendation import AIRecommendation, NurseDecision, ModelStatus
from app.models.queue_entry import QueueEntry
from app.models.audit import AuditEvent
from app.models.notification import Notification   # required so SQLAlchemy resolves Encounter.notifications
from app.models.device import Device               # required so SQLAlchemy resolves all relationships

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

now = datetime.now(timezone.utc)
mins = lambda n: now - timedelta(minutes=n)
secs_from_now = lambda n: now + timedelta(seconds=n)


# ── Demo Users ─────────────────────────────────────────────────────────────

DEMO_USERS = [
    {
        "staff_id": "TN-0421",
        "name": "Sr. Priya Sharma",
        "role": UserRole.TRIAGE_NURSE,
        "department": "Emergency",
        "password": "demo123",
    },
    {
        "staff_id": "CL-0112",
        "name": "Dr. Anand Rajan",
        "role": UserRole.CLINICIAN,
        "department": "Emergency",
        "password": "demo123",
    },
    {
        "staff_id": "AD-0031",
        "name": "Admin Suresh Nair",
        "role": UserRole.ADMINISTRATOR,
        "department": "Administration",
        "password": "demo123",
    },
]


# ── Synthetic Patients (mirrors mockPatients.ts exactly) ───────────────────

PATIENTS = [
    # 1. Critical adult — chest pain, shock
    {
        "display_id": "P-10241", "name": "Rajesh Kumar", "age": 58, "sex": "Male",
        "age_group": AgeGroup.OLDER_ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 22,
        "chief_complaint": "Severe chest pain, radiating to arm, sweating profusely",
        "symptoms": ["Chest pain", "Diaphoresis", "Arm pain", "Nausea"],
        "danger_signs": ["Severe distress"],
        "vitals": {"spo2": 90, "heart_rate": 124, "respiratory_rate": 28, "bp_systolic": 88, "bp_diastolic": 60, "temperature": 37.1, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Hypertension", "Type 2 Diabetes"], "medications": ["Metformin", "Amlodipine"], "allergies": ["Penicillin"]},
        "acuity": Acuity.CRITICAL, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 94, "reassessment_seconds": -120,
        "nurse_action": "ACCEPTED",
    },
    # 2. High-acuity — respiratory distress
    {
        "display_id": "P-10242", "name": "Anjali Mehta", "age": 34, "sex": "Female",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 18,
        "chief_complaint": "Difficulty breathing, worsening over last 2 hours",
        "symptoms": ["Dyspnea", "Wheezing", "Chest tightness"],
        "danger_signs": ["Breathing difficulty"],
        "vitals": {"spo2": 91, "heart_rate": 118, "respiratory_rate": 29, "bp_systolic": 104, "bp_diastolic": 68, "temperature": 37.8, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Asthma"], "medications": ["Salbutamol inhaler"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 87, "reassessment_seconds": 138,
        "nurse_action": "ACCEPTED",
    },
    # 3. Moderate — fever + headache + meningism signs
    {
        "display_id": "P-10243", "name": "Suresh Pillai", "age": 42, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 35,
        "chief_complaint": "High fever and severe headache for 2 days",
        "symptoms": ["Fever", "Headache", "Neck stiffness", "Photophobia"],
        "danger_signs": [],
        "vitals": {"spo2": 97, "heart_rate": 102, "respiratory_rate": 20, "bp_systolic": 118, "bp_diastolic": 76, "temperature": 39.4, "avpu": "Alert"},
        "history": {"available": True, "conditions": [], "medications": [], "allergies": ["Sulfa drugs"]},
        "acuity": Acuity.MODERATE, "safety_status": SafetyStatus.VERIFY,
        "confidence": 78, "reassessment_seconds": 420,
        "nurse_action": "ACCEPTED",
    },
    # 4. Low — minor ankle sprain
    {
        "display_id": "P-10244", "name": "Meena Reddy", "age": 27, "sex": "Female",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 52,
        "chief_complaint": "Twisted ankle while walking, mild pain and swelling",
        "symptoms": ["Ankle pain", "Swelling", "Difficulty walking"],
        "danger_signs": [],
        "vitals": {"spo2": 99, "heart_rate": 76, "respiratory_rate": 16, "bp_systolic": 118, "bp_diastolic": 72, "temperature": 36.8, "avpu": "Alert"},
        "history": {"available": False},
        "acuity": Acuity.LOW, "safety_status": SafetyStatus.NORMAL,
        "confidence": 91, "reassessment_seconds": 1800,
        "nurse_action": "ACCEPTED",
    },
    # 5. Ambiguous — vague symptoms, cardiac history, low confidence
    {
        "display_id": "P-10245", "name": "Prakash Iyer", "age": 61, "sex": "Male",
        "age_group": AgeGroup.OLDER_ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 28,
        "chief_complaint": "I feel weak and something feels very wrong. Not sure what.",
        "symptoms": ["Generalised weakness", "Malaise"],
        "danger_signs": [],
        "vitals": {"spo2": 95, "heart_rate": 94, "respiratory_rate": 18, "bp_systolic": 112, "bp_diastolic": 74, "temperature": 37.3, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Ischaemic heart disease"], "medications": ["Aspirin", "Atorvastatin"], "allergies": []},
        "acuity": Acuity.MODERATE, "safety_status": SafetyStatus.VERIFY,
        "confidence": 52, "reassessment_seconds": 240,
        "nurse_action": None,
    },
    # 6. Pediatric — 3-year-old, high fever
    {
        "display_id": "P-10246", "name": "Aarav Sharma", "age": 3, "sex": "Male",
        "age_group": AgeGroup.PEDIATRIC, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 15,
        "chief_complaint": "High fever and crying inconsolably, not eating since morning",
        "symptoms": ["Fever", "Inconsolable crying", "Poor feeding", "Irritability"],
        "danger_signs": [],
        "vitals": {"spo2": 96, "heart_rate": 148, "respiratory_rate": 34, "bp_systolic": 94, "bp_diastolic": 58, "temperature": 39.8, "avpu": "Alert"},
        "history": {"available": True, "conditions": [], "medications": [], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 83, "reassessment_seconds": 300,
        "nurse_action": None,
    },
    # 7. Geriatric — fall, anticoagulant, hip fracture
    {
        "display_id": "P-10247", "name": "Saraswati Devi", "age": 82, "sex": "Female",
        "age_group": AgeGroup.OLDER_ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 40,
        "chief_complaint": "Fell at home, hip pain, unable to stand",
        "symptoms": ["Hip pain", "Fall", "Inability to weight-bear"],
        "danger_signs": ["Major trauma"],
        "vitals": {"spo2": 93, "heart_rate": 96, "respiratory_rate": 22, "bp_systolic": 108, "bp_diastolic": 64, "temperature": 36.4, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Osteoporosis", "Atrial fibrillation", "Hypertension"], "medications": ["Warfarin", "Bisoprolol", "Amlodipine"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 80, "reassessment_seconds": 600,
        "nurse_action": "ACCEPTED",
    },
    # 8. Zero-history patient — unconscious at roadside
    {
        "display_id": "P-10248", "name": None, "age": 33, "sex": "Unknown",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 10,
        "chief_complaint": "Found unconscious by roadside, brought by passersby",
        "symptoms": ["Altered consciousness", "Unknown history"],
        "danger_signs": ["Altered consciousness"],
        "vitals": {"spo2": 94, "heart_rate": 108, "respiratory_rate": 24, "bp_systolic": 96, "bp_diastolic": 62, "temperature": 36.1, "avpu": "Pain"},
        "history": {"available": False},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 71, "reassessment_seconds": 180,
        "nurse_action": None,
    },
    # 9. Missing vitals — abdominal pain
    {
        "display_id": "P-10249", "name": "Deepak Joshi", "age": 45, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 20,
        "chief_complaint": "Abdominal pain, worse after eating",
        "symptoms": ["Abdominal pain", "Nausea", "Bloating"],
        "danger_signs": [],
        "vitals": {"spo2": None, "heart_rate": 88, "respiratory_rate": 18, "bp_systolic": None, "bp_diastolic": None, "temperature": None, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["GERD"], "medications": ["Omeprazole"], "allergies": []},
        "acuity": Acuity.MODERATE, "safety_status": SafetyStatus.VERIFY,
        "confidence": 61, "reassessment_seconds": 900,
        "nurse_action": None,
    },
    # 10. Conflicting data — tachycardia + hypotension + normal SpO2
    {
        "display_id": "P-10250", "name": "Fatima Sheikh", "age": 52, "sex": "Female",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.REFERRAL,
        "arrival_minutes_ago": 45,
        "chief_complaint": "Dizziness and palpitations",
        "symptoms": ["Dizziness", "Palpitations", "Lightheadedness"],
        "danger_signs": [],
        "vitals": {"spo2": 99, "heart_rate": 142, "respiratory_rate": 17, "bp_systolic": 82, "bp_diastolic": 50, "temperature": 36.9, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Hypothyroidism"], "medications": ["Levothyroxine"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 68, "reassessment_seconds": -300,
        "nurse_action": "ACCEPTED",
    },
    # 11. Deteriorating — SpO2 dropped
    {
        "display_id": "P-10251", "name": "Mohan Das", "age": 49, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 60,
        "chief_complaint": "Mild shortness of breath, thought it was nothing",
        "symptoms": ["Dyspnea", "Fatigue", "Cough"],
        "danger_signs": ["Breathing difficulty"],
        "vitals": {"spo2": 91, "heart_rate": 112, "respiratory_rate": 27, "bp_systolic": 110, "bp_diastolic": 70, "temperature": 37.6, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Smoker (20 pack-years)"], "medications": [], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 85, "reassessment_seconds": 120,
        "nurse_action": None,
    },
    # 12. Nurse override case — thunderclap headache
    {
        "display_id": "P-10252", "name": "Ritu Agarwal", "age": 38, "sex": "Female",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 55,
        "chief_complaint": "Severe headache, sudden onset, worst of life",
        "symptoms": ["Sudden onset headache", "Photophobia", "Vomiting"],
        "danger_signs": [],
        "vitals": {"spo2": 98, "heart_rate": 88, "respiratory_rate": 18, "bp_systolic": 162, "bp_diastolic": 94, "temperature": 37.0, "avpu": "Alert"},
        "history": {"available": False},
        "acuity": Acuity.CRITICAL, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 65, "reassessment_seconds": 900,
        "nurse_action": "OVERRIDE",
        "override_reason": "Clinical deterioration",
        "override_note": '"Thunderclap" headache pattern — possible SAH. Immediate review.',
        "ai_acuity": Acuity.MODERATE,
    },
    # 13. Trauma — road traffic accident
    {
        "display_id": "P-10253", "name": "Arjun Singh", "age": 22, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 8,
        "chief_complaint": "Road traffic accident, multiple injuries",
        "symptoms": ["Chest pain", "Abdominal pain", "Head injury", "Lacerations"],
        "danger_signs": ["Major trauma", "Severe bleeding"],
        "vitals": {"spo2": 92, "heart_rate": 132, "respiratory_rate": 30, "bp_systolic": 86, "bp_diastolic": 54, "temperature": 35.8, "avpu": "Voice"},
        "history": {"available": False},
        "acuity": Acuity.CRITICAL, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 96, "reassessment_seconds": None,
        "nurse_action": None,
        "status": PatientStatus.IN_PROGRESS,
    },
    # 14. Stroke — FAST positive, within treatment window
    {
        "display_id": "P-10254", "name": "Vandana Mishra", "age": 67, "sex": "Female",
        "age_group": AgeGroup.OLDER_ADULT, "arrival_mode": ArrivalMode.REFERRAL,
        "arrival_minutes_ago": 30,
        "chief_complaint": "Sudden weakness in left arm and face drooping, started 90 minutes ago",
        "symptoms": ["Facial droop", "Left arm weakness", "Speech difficulty", "Sudden onset"],
        "danger_signs": [],
        "vitals": {"spo2": 96, "heart_rate": 86, "respiratory_rate": 18, "bp_systolic": 176, "bp_diastolic": 100, "temperature": 36.9, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Hypertension", "Diabetes"], "medications": ["Metformin", "Amlodipine", "Aspirin"], "allergies": []},
        "acuity": Acuity.CRITICAL, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 91, "reassessment_seconds": -600,
        "nurse_action": "ACCEPTED",
    },
    # 15. Low confidence — vague complaint, no history
    {
        "display_id": "P-10255", "name": "Kiran Patel", "age": 29, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 25,
        "chief_complaint": "Just not feeling well, tired",
        "symptoms": ["Fatigue", "Malaise"],
        "danger_signs": [],
        "vitals": {"spo2": 97, "heart_rate": 82, "respiratory_rate": 16, "bp_systolic": 116, "bp_diastolic": 74, "temperature": 37.1, "avpu": "Alert"},
        "history": {"available": False},
        "acuity": Acuity.LOW, "safety_status": SafetyStatus.VERIFY,
        "confidence": 46, "reassessment_seconds": 1200,
        "nurse_action": None,
    },
    # 16. Device disconnected — CAD patient, stale vitals
    {
        "display_id": "P-10256", "name": "Sunita Bose", "age": 55, "sex": "Female",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 12,
        "chief_complaint": "Chest tightness and shortness of breath on exertion",
        "symptoms": ["Chest tightness", "Exertional dyspnea", "Fatigue"],
        "danger_signs": ["Breathing difficulty"],
        "vitals": {"spo2": 94, "heart_rate": 96, "respiratory_rate": 22, "bp_systolic": 128, "bp_diastolic": 80, "temperature": 37.0, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Known CAD"], "medications": ["Isosorbide mononitrate", "Aspirin"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 74, "reassessment_seconds": 600,
        "nurse_action": None,
    },
    # 17. Neurological — seizure, post-ictal
    {
        "display_id": "P-10257", "name": "Ramesh Gupta", "age": 36, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.AMBULANCE,
        "arrival_minutes_ago": 7,
        "chief_complaint": "Witnessed seizure lasting 3 minutes, now confused",
        "symptoms": ["Seizure", "Post-ictal confusion", "Tongue biting"],
        "danger_signs": ["Seizure", "Altered consciousness"],
        "vitals": {"spo2": 95, "heart_rate": 104, "respiratory_rate": 20, "bp_systolic": 140, "bp_diastolic": 88, "temperature": 37.5, "avpu": "Voice"},
        "history": {"available": True, "conditions": ["Epilepsy"], "medications": ["Sodium valproate"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.VERIFY,
        "confidence": 88, "reassessment_seconds": 300,
        "nurse_action": None,
    },
    # 18. Diabetic emergency — hypoglycemia
    {
        "display_id": "P-10258", "name": "Geeta Nair", "age": 63, "sex": "Female",
        "age_group": AgeGroup.OLDER_ADULT, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 5,
        "chief_complaint": "Found shaking and sweating, blood sugar very low at home (2.4 mmol/L)",
        "symptoms": ["Diaphoresis", "Tremors", "Confusion", "Pallor"],
        "danger_signs": ["Altered consciousness"],
        "vitals": {"spo2": 97, "heart_rate": 116, "respiratory_rate": 19, "bp_systolic": 98, "bp_diastolic": 62, "temperature": 36.2, "avpu": "Voice"},
        "history": {"available": True, "conditions": ["Type 2 Diabetes", "Hypertension"], "medications": ["Insulin glargine", "Metformin"], "allergies": []},
        "acuity": Acuity.HIGH, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 90, "reassessment_seconds": 180,
        "nurse_action": None,
    },
    # 19. Paediatric — 8 months, breathing difficulty
    {
        "display_id": "P-10259", "name": "Baby Priya (8mo)", "age": 0, "sex": "Female",
        "age_group": AgeGroup.PEDIATRIC, "arrival_mode": ArrivalMode.WALK_IN,
        "arrival_minutes_ago": 11,
        "chief_complaint": "8-month-old with breathing difficulty and grunting for 2 hours",
        "symptoms": ["Grunting", "Tachypnoea", "Intercostal recession", "Cyanosis"],
        "danger_signs": ["Breathing difficulty", "Severe distress"],
        "vitals": {"spo2": 88, "heart_rate": 172, "respiratory_rate": 58, "bp_systolic": 72, "bp_diastolic": 44, "temperature": 38.9, "avpu": "Alert"},
        "history": {"available": True, "conditions": [], "medications": [], "allergies": []},
        "acuity": Acuity.CRITICAL, "safety_status": SafetyStatus.URGENT_REVIEW,
        "confidence": 94, "reassessment_seconds": 60,
        "nurse_action": None,
    },
    # 20. Psychiatric emergency — self-harm risk
    {
        "display_id": "P-10260", "name": "Anil Verma", "age": 24, "sex": "Male",
        "age_group": AgeGroup.ADULT, "arrival_mode": ArrivalMode.REFERRAL,
        "arrival_minutes_ago": 19,
        "chief_complaint": "Self-harm — lacerations to forearm, accompanied by family",
        "symptoms": ["Lacerations", "Distress", "Agitation"],
        "danger_signs": ["Severe bleeding", "Severe distress"],
        "vitals": {"spo2": 98, "heart_rate": 98, "respiratory_rate": 18, "bp_systolic": 122, "bp_diastolic": 78, "temperature": 36.8, "avpu": "Alert"},
        "history": {"available": True, "conditions": ["Depression"], "medications": ["Sertraline"], "allergies": []},
        "acuity": Acuity.MODERATE, "safety_status": SafetyStatus.VERIFY,
        "confidence": 72, "reassessment_seconds": 900,
        "nurse_action": None,
    },
]


# ── Seed helpers ───────────────────────────────────────────────────────────

async def seed_users(session: AsyncSession) -> dict:
    """Create demo users. Returns {staff_id: User} mapping."""
    user_map = {}
    for u in DEMO_USERS:
        existing = await session.execute(select(User).where(User.staff_id == u["staff_id"]))
        if existing.scalar_one_or_none():
            print(f"  [SKIP] User {u['staff_id']} already exists")
            result = await session.execute(select(User).where(User.staff_id == u["staff_id"]))
            user_map[u["staff_id"]] = result.scalar_one()
            continue

        user = User(
            staff_id=u["staff_id"],
            name=u["name"],
            role=u["role"],
            department=u["department"],
            hashed_password=hash_password(u["password"]),
            is_active=True,
        )
        session.add(user)
        await session.flush()
        user_map[u["staff_id"]] = user
        print(f"  [OK] Created user {u['staff_id']} ({u['role'].value})")
    return user_map


async def seed_patient(session: AsyncSession, data: dict, nurse: User) -> None:
    """Create one synthetic patient with full encounter, assessment, vitals, recommendation."""
    display_id = data["display_id"]

    # Skip if already seeded
    existing = await session.execute(select(Patient).where(Patient.display_id == display_id))
    if existing.scalar_one_or_none():
        print(f"  [SKIP] {display_id} already exists")
        return

    # --- Patient ---
    patient = Patient(
        display_id=display_id,
        name=data["name"],
        age=data["age"],
        sex=data["sex"],
        age_group=data["age_group"],
        is_simulation=True,
    )
    session.add(patient)
    await session.flush()

    # --- Encounter ---
    arrival_time = mins(data["arrival_minutes_ago"])
    status = data.get("status", PatientStatus.WAITING)
    encounter = Encounter(
        patient_id=patient.id,
        arrival_time=arrival_time,
        arrival_mode=data["arrival_mode"],
        status=status,
        current_acuity=data["acuity"],
        safety_status=data["safety_status"],
        waiting_time_seconds=data["arrival_minutes_ago"] * 60,
        reassessment_count=1 if data.get("nurse_action") else 0,
        last_updated=now,
        device_connected=False,
        is_surge_patient=False,
        reassessment_due=(
            now + timedelta(seconds=data["reassessment_seconds"])
            if data.get("reassessment_seconds") is not None
            else None
        ),
    )
    session.add(encounter)
    await session.flush()

    # --- Assessment ---
    hist = data.get("history", {})
    assessment = Assessment(
        encounter_id=encounter.id,
        assessment_type=AssessmentType.INITIAL,
        chief_complaint=data["chief_complaint"],
        confirmed_complaint=data["chief_complaint"],
        symptoms=data["symptoms"],
        danger_signs=data["danger_signs"],
        none_observed=len(data["danger_signs"]) == 0,
        history_status=HistoryStatus.AVAILABLE if hist.get("available") else HistoryStatus.UNAVAILABLE,
        history_conditions=hist.get("conditions"),
        history_medications=hist.get("medications"),
        history_allergies=hist.get("allergies"),
        submitted_by_id=nurse.id,
        submitted_at=arrival_time + timedelta(minutes=2),
    )
    session.add(assessment)
    await session.flush()

    # --- Vitals ---
    v = data["vitals"]
    avpu_val = None
    if v.get("avpu"):
        avpu_map = {"Alert": AVPU.ALERT, "Voice": AVPU.VOICE, "Pain": AVPU.PAIN, "Unresponsive": AVPU.UNRESPONSIVE}
        avpu_val = avpu_map.get(v["avpu"])

    vital = Vital(
        encounter_id=encounter.id,
        assessment_id=assessment.id,
        spo2=v.get("spo2"),
        heart_rate=v.get("heart_rate"),
        respiratory_rate=v.get("respiratory_rate"),
        bp_systolic=v.get("bp_systolic"),
        bp_diastolic=v.get("bp_diastolic"),
        temperature=v.get("temperature"),
        avpu=avpu_val,
        source=VitalSource.MANUAL,
        measured_at=arrival_time + timedelta(minutes=3),
    )
    session.add(vital)
    await session.flush()

    # --- AI Recommendation ---
    safety_reasons = []
    if data["safety_status"] == SafetyStatus.URGENT_REVIEW:
        safety_reasons.append("High-risk clinical signal detected")
    elif data["safety_status"] == SafetyStatus.VERIFY:
        safety_reasons.append("Clinical verification recommended")

    recommendation = AIRecommendation(
        assessment_id=assessment.id,
        encounter_id=encounter.id,
        acuity=data.get("ai_acuity", data["acuity"]),
        confidence=data["confidence"],
        data_completeness=85.0 if hist.get("available") else 65.0,
        safety_status=data["safety_status"],
        safety_flag=safety_reasons[0] if safety_reasons else None,
        key_reasons=["Simulated assessment — see chief complaint"],
        clinical_rules=safety_reasons,
        top_factors=[{"feature": "Chief Complaint", "value": data["chief_complaint"][:40], "impact": "HIGH", "direction": "INCREASING"}],
        model_version="mock-v1.0",
        model_status=ModelStatus.MOCK,
        clinical_rule_version="prototype-v1.0",
        is_conservative=data["confidence"] < 70,
        recommended_at=arrival_time + timedelta(minutes=4),
    )
    session.add(recommendation)
    await session.flush()

    # --- Nurse Decision (if applicable) ---
    if data.get("nurse_action") == "ACCEPTED":
        decision = NurseDecision(
            assessment_id=assessment.id,
            nurse_id=nurse.id,
            action="ACCEPTED",
            final_acuity=data["acuity"],
            decided_at=arrival_time + timedelta(minutes=5),
        )
        session.add(decision)
        await session.flush()
    elif data.get("nurse_action") == "OVERRIDE":
        decision = NurseDecision(
            assessment_id=assessment.id,
            nurse_id=nurse.id,
            action="OVERRIDE",
            final_acuity=data["acuity"],
            override_reason=data.get("override_reason", "Clinical deterioration"),
            override_note=data.get("override_note"),
            decided_at=arrival_time + timedelta(minutes=5),
        )
        session.add(decision)
        await session.flush()

    # --- Queue Entry ---
    acuity_rank = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "PENDING": 4}.get(data["acuity"].value, 4)
    safety_bonus = 100 if data["safety_status"] == SafetyStatus.URGENT_REVIEW else 0
    queue_entry = QueueEntry(
        encounter_id=encounter.id,
        priority_score=acuity_rank * 1000 - safety_bonus,
        acuity_rank=acuity_rank,
        reassessment_overdue=(
            data.get("reassessment_seconds") is not None and data["reassessment_seconds"] < 0
        ),
        has_safety_flag=data["safety_status"] != SafetyStatus.NORMAL,
        last_priority_update=now,
    )
    session.add(queue_entry)

    # --- Audit Event ---
    audit = AuditEvent(
        timestamp=arrival_time + timedelta(minutes=5),
        user_id=nurse.id,
        user_staff_id=nurse.staff_id,
        user_name=nurse.name,
        user_role=nurse.role.value,
        event_type=data.get("nurse_action", "ASSESSMENT_CREATED") or "ASSESSMENT_CREATED",
        patient_id=patient.id,
        patient_display_id=display_id,
        encounter_id=encounter.id,
        assessment_id=assessment.id,
        ai_recommendation=data.get("ai_acuity", data["acuity"]).value,
        ai_confidence=float(data["confidence"]),
        safety_flag=safety_reasons[0] if safety_reasons else None,
        nurse_action=data.get("nurse_action"),
        final_acuity=data["acuity"].value,
        override_reason=data.get("override_reason"),
        model_version="mock-v1.0",
        notes=data.get("override_note"),
    )
    session.add(audit)
    await session.flush()

    print(f"  [OK] {display_id} — {data['name'] or 'Unknown'} ({data['acuity'].value})")


async def main():
    print("\n========================================")
    print("  VitalNode Seed Script")
    print("  Prototype — Synthetic Data Only")
    print("========================================\n")

    async with SessionLocal() as session:
        async with session.begin():
            print("Creating demo users...")
            user_map = await seed_users(session)
            nurse = user_map.get("TN-0421")
            if not nurse:
                print("ERROR: Could not create/find nurse TN-0421")
                return

            print(f"\nSeeding {len(PATIENTS)} synthetic patients...")
            for patient_data in PATIENTS:
                await seed_patient(session, patient_data, nurse)

    print(f"\n✅ Seed complete.")
    print(f"   Users: {len(DEMO_USERS)}")
    print(f"   Patients: {len(PATIENTS)}")
    print("\nDemo credentials:")
    for u in DEMO_USERS:
        print(f"   {u['staff_id']} / demo123  ({u['role'].value})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
