# VitalNode Backend — Implementation Plan

> Prototype for Accenture Innovation Challenge 2026  
> NOT clinically validated. NOT for real patient care.  
> Synthetic data only.

---

## 1. Frontend Analysis Summary

Inspected the complete VitalNode React frontend before writing any backend code.

### Frontend state (Zustand store) — 100% local mock, no API calls
- All data lives in `appStore.ts` using Zustand
- `mockPatients.ts` seeds 16 synthetic patients on startup
- No `fetch()`, no `axios`, no API client exists anywhere
- All actions (login, createPatient, acceptRecommendation, override, triggerReassessment) are local state mutations

### Frontend data shapes identified

| Shape | Notes |
|---|---|
| `User` | `{ id, name, role, staffId, department }` — roles: "Triage Nurse" / "Clinician" / "Administrator" |
| `Patient` | Full shape with `id=encounter_id`, `displayId`, demographics, vitals, history, aiRecommendation, nurseDecision |
| `Vitals` | `{ spo2, heartRate, respiratoryRate, bpSystolic, bpDiastolic, temperature, avpu, timestamp, source }` |
| `AcuityRecommendation` | `{ acuity, confidence, safetyStatus, safetyFlag, dataCompleteness, keyReasons, clinicalRules, topFactors, modelVersion, isConservative }` |
| `NurseDecision` | `{ action, finalAcuity, overrideReason, overrideNote, nurseId, nurseName, timestamp }` |
| `AuditEntry` | `{ id, timestamp, patientId, patientDisplayId, eventType, aiRecommendation, aiConfidence, nurseAction, finalAcuity, overrideReason, modelVersion, nurseId, nurseName }` |
| `Notification` | `{ id, type, message, patientId, patientDisplayId, timestamp, read, urgent }` |

### Frontend screens mapped
| Screen | Backend support needed |
|---|---|
| LoginScreen | POST /api/v1/auth/login |
| DashboardScreen | GET /api/v1/queue/summary, GET /api/v1/patients/search |
| PatientQueueScreen | GET /api/v1/queue |
| NewAssessmentScreen | POST /api/v1/patients/assess |
| AIResultScreen | POST /api/v1/assessments/{id}/decision |
| PatientDetailScreen | GET patient, GET /api/v1/patients/{id}/timeline |
| ReassessmentScreen | GET /api/v1/reassessments, POST /api/v1/reassessments/{id} |
| AuditLogScreen | GET /api/v1/audit |
| SurgeModeScreen | POST /api/v1/surge/start, POST /api/v1/surge/stop |
| AnalyticsScreen | GET /api/v1/queue/summary, GET /api/v1/audit |
| SettingsScreen | GET /api/v1/system/config (admin) |
| SystemInfoScreen | GET /api/v1/system/status (admin) |

---

## 2. Architecture Decisions

### Why encounter ≠ patient
A `Patient` is a person identity (demographics).  
An `Encounter` is a single emergency visit.  
The frontend uses encounter ID as the patient ID in the queue (matches existing mock data pattern).

### Why all vitals are stored as new rows
Deterioration detection requires comparing consecutive readings.  
Overwriting would lose the trend. Every measurement creates a new `Vital` row.

### Why AI recommendation is immutable
Override must not delete the original AI recommendation — the difference between AI acuity and nurse-confirmed acuity is the audit record. Both must be preserved.

### Why safety gate is separate from ML
Safety rules must work even when the ML model is unavailable. They are evaluated independently and can only escalate, never downgrade, the final safety status.

---

## 3. Full Pipeline

```
NURSE INPUT (NewAssessmentScreen)
         ↓
POST /api/v1/patients/assess
         ↓
PatientService → creates Patient + Encounter + Assessment + Vital + QueueEntry
         ↓
AssessmentService.run_ai_assessment()
         ↓
   ┌─────────────────────────────────────┐
   │  1. get_latest_vital                │
   │  2. compute_data_quality            │
   │  3. build MLFeatures                │
   │  4. evaluate_clinical_rules         │
   │  5. ml_engine.predict(features)     │
   │  6. decision_fusion.fuse(...)       │
   │  7. safety_gate.run_safety_gate(...)│
   └─────────────────────────────────────┘
         ↓
AIRecommendation stored (immutable)
         ↓
Encounter priority updated (QueueEntry)
Reassessment timer set
Audit event recorded
         ↓
Response → frontend (Patient shape)

NURSE DECISION (AIResultScreen)
         ↓
POST /api/v1/assessments/{id}/decision
         ↓
NurseDecision stored (AI recommendation unchanged)
Encounter acuity updated
Notification created (if override)
Audit event recorded
```

---

## 4. Role Permissions

| Endpoint | Triage Nurse | Clinician | Administrator |
|---|---|---|---|
| POST /auth/login | ✅ | ✅ | ✅ |
| GET /auth/me | ✅ | ✅ | ✅ |
| POST /patients/assess | ✅ | ✅ | ✅ |
| GET /queue | ✅ | ✅ | ✅ |
| POST /assessments/{id}/decision | ✅ | ✅ | ✅ |
| GET /audit | ✅ | ✅ | ✅ |
| POST /surge/start | ✅ | ✅ | ✅ |
| GET /system/status | ❌ | ❌ | ✅ |
| GET /system/config | ❌ | ❌ | ✅ |
| POST /demo/* | ✅ (DEMO_MODE only) | ✅ | ✅ |

---

## 5. ML Integration Path

Current state: `MockMLEngine` is active.  
To plug in real XGBoost:

1. Set `ML_ENGINE=xgboost` in `.env`
2. Set `MODEL_PATH=/path/to/model.json`
3. Install: `pip install xgboost`
4. Implement `XGBoostMLEngine.predict()` in `app/ml/xgboost_engine.py`
5. Map `MLFeatures` → model's expected feature vector
6. No other files need changing

The `MLFeatures` dataclass is the contract. The rest of the pipeline is model-agnostic.

---

## 6. Limitations (prototype)

- Model is MOCK — all predictions are deterministic rule-based simulations
- Clinical thresholds are illustrative, NOT clinically validated
- No real patient data is used anywhere
- ABDM/FHIR integration is architecture-only (no live connection)
- Voice transcription returns mock data unless SPEECH_PROVIDER is configured
- Surge state is in-memory (resets on server restart)
- No WebSocket real-time updates (frontend uses local state polling)
- Single-process deployment only (no horizontal scaling)

---

## 7. Files Created

```
vitalnode-backend/
├── app/
│   ├── main.py                          ← FastAPI app, all routers, error handlers
│   ├── core/
│   │   ├── config.py                    ← Settings (pydantic-settings, .env)
│   │   ├── security.py                  ← bcrypt + JWT
│   │   ├── logging.py                   ← structlog structured logging
│   │   └── exceptions.py               ← Domain exceptions
│   ├── db/
│   │   └── database.py                  ← Async SQLAlchemy engine + session
│   ├── models/
│   │   ├── user.py                      ← User, UserRole
│   │   ├── patient.py                   ← Patient, AgeGroup, Sex
│   │   ├── encounter.py                 ← Encounter, ArrivalMode, PatientStatus, Acuity, SafetyStatus
│   │   ├── assessment.py               ← Assessment, HistoryStatus
│   │   ├── vital.py                     ← Vital, VitalSource, AVPU
│   │   ├── recommendation.py           ← AIRecommendation, NurseDecision
│   │   ├── queue_entry.py              ← QueueEntry
│   │   ├── audit.py                     ← AuditEvent (immutable)
│   │   ├── notification.py             ← Notification
│   │   └── device.py                    ← Device
│   ├── schemas/
│   │   ├── auth.py                      ← LoginRequest, LoginResponse, UserResponse
│   │   ├── patient.py                   ← PatientResponse, FullPatientResponse
│   │   ├── assessment.py               ← AssessmentCreate, VitalsCreate, NurseDecisionCreate, DataQualityResponse
│   │   └── recommendation.py           ← RecommendationResponse, AuditEntryResponse, NotificationResponse
│   ├── api/v1/
│   │   ├── deps.py                      ← Auth dependencies, role guards
│   │   ├── auth.py                      ← /auth/login, /auth/me, /auth/logout
│   │   ├── patients.py                  ← /patients/assess, /patients/search, /patients/{id}/timeline
│   │   ├── assessments.py              ← /assessments/{id}/predict, /decision, /quality
│   │   ├── queue.py                     ← /queue, /queue/summary
│   │   ├── reassessments.py            ← /reassessments, /reassessments/{id}
│   │   ├── notifications.py            ← /notifications, /notifications/{id}/read
│   │   ├── audit.py                     ← /audit
│   │   ├── surge.py                     ← /surge/start, /surge/stop, /surge/status
│   │   ├── devices.py                   ← /devices (register, list, simulate, disconnect)
│   │   ├── voice.py                     ← /voice/transcribe, /voice/extract-symptoms
│   │   ├── system.py                    ← /system/status, /system/config (admin only)
│   │   └── demo.py                      ← /demo/* (DEMO_MODE only)
│   ├── services/
│   │   ├── auth_service.py             ← authenticate_user, issue_token
│   │   ├── patient_service.py          ← create_patient_and_encounter, search, update_priority
│   │   ├── assessment_service.py       ← run_ai_assessment (full pipeline), record_nurse_decision
│   │   ├── vital_service.py            ← store_vital, validate, detect_deterioration
│   │   ├── data_quality_service.py     ← compute_data_quality
│   │   ├── clinical_rules.py           ← evaluate_clinical_rules (INDEPENDENT from ML)
│   │   ├── decision_fusion.py          ← fuse(ml + rules + quality)
│   │   ├── safety_gate.py              ← run_safety_gate (final check)
│   │   ├── queue_service.py            ← get_queue (priority-ordered)
│   │   ├── reassessment_service.py     ← trigger_reassessment, get_overdue
│   │   ├── notification_service.py     ← create/get/mark_read
│   │   └── audit_service.py            ← record_audit_event (insert-only)
│   ├── ml/
│   │   ├── interface.py                ← MLEngine ABC, MLFeatures, MLPrediction
│   │   ├── mock_engine.py              ← MockMLEngine (MOCK status, deterministic)
│   │   └── xgboost_engine.py          ← XGBoostMLEngine (plug-in point, NotImplemented)
│   └── workers/
│       └── reassessment_worker.py      ← Background timer check loop
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/0001_initial_schema.py ← All 11 tables + enums
├── tests/
│   ├── conftest.py                      ← Fixtures, in-memory SQLite, test client
│   ├── test_auth.py                     ← Login, /me, role enforcement
│   ├── test_vitals.py                   ← Technical validity, BP conflict, missing OK
│   ├── test_clinical_rules.py          ← Safety escalation, AVPU, pediatric, low data
│   ├── test_safety_gate.py             ← Safety gate + decision fusion + ML mock
│   ├── test_danger_signs.py            ← none_observed conflict validation
│   ├── test_data_quality.py            ← Completeness, stale, conflicts
│   ├── test_queue.py                   ← Priority ordering, acuity dominance
│   └── test_assessment_api.py          ← Full HTTP integration tests
├── seed.py                             ← 3 users + 20 synthetic patients
├── requirements.txt
├── alembic.ini
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── BACKEND_IMPLEMENTATION_PLAN.md      ← This file
└── README.md
```
