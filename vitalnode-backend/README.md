# VitalNode Backend

FastAPI backend for the VitalNode emergency triage prototype, built for the Accenture Innovation Challenge 2026.

The backend handles authentication, patient intake, assessment persistence, AI recommendation generation, clinical safety rules, reassessment timers, queue ordering, notifications, audit logging, surge-mode scenarios, voice transcription, device simulation, and system configuration.

Responsible-use notice: this service is for challenge evaluation only. It is not clinically validated, is not a medical device, and must not be used for real patient care, diagnosis, or treatment.

## Deployed service

| Resource | Link |
| --- | --- |
| Backend API | [https://vitalnode-backend.onrender.com](https://vitalnode-backend.onrender.com) |
| Swagger / OpenAPI UI | [https://vitalnode-backend.onrender.com/docs](https://vitalnode-backend.onrender.com/docs) |
| ReDoc | [https://vitalnode-backend.onrender.com/redoc](https://vitalnode-backend.onrender.com/redoc) |
| Health check | [https://vitalnode-backend.onrender.com/health](https://vitalnode-backend.onrender.com/health) |

The deployed frontend is [https://vital-node.onrender.com/](https://vital-node.onrender.com/).

## Demo credentials

| Staff ID | Password | Role |
| --- | --- | --- |
| `TN-0421` | `demo123` | Triage Nurse |
| `CL-0112` | `demo123` | Clinician |
| `AD-0031` | `demo123` | Administrator |

## Core request flow

```text
POST /api/v1/patients/assess
        |
        v
PatientService creates or updates:
  Patient -> Encounter -> Assessment -> Vital -> QueueEntry
        |
        v
AssessmentService.run_ai_assessment()
  compute_data_quality()
  evaluate_clinical_rules()
  ml_engine.predict()
  decision_fusion.fuse()
  safety_gate.run_safety_gate()
        |
        v
AIRecommendation is stored
        |
        v
POST /api/v1/assessments/{id}/decision
        |
        v
Staff accept | override | request reassessment
        |
        v
Queue priority, reassessment timer, audit log, and WebSocket updates
```

The AI recommendation is not treated as the final queue decision until a staff action is recorded.

## API overview

All routes below are prefixed with `/api/v1`, except `/health`.

| Area | Routes | Purpose |
| --- | --- | --- |
| Auth | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | Staff sessions and audit-aware logout. |
| Patients | `POST /patients/assess`, `GET /patients/search`, `GET /patients/{id}/timeline` | Intake, search, and patient timeline. |
| Assessments | `POST /assessments/{id}/predict`, `POST /assessments/{id}/decision`, `GET /assessments/{id}/quality` | AI pipeline, staff decision, and data quality. |
| Queue | `GET /queue`, `GET /queue/summary`, `POST /queue/{id}/complete` | Ordered queue, summary, and bed assignment. |
| Reassessment | `GET /reassessments`, `POST /reassessments/{id}` | Due cases and manual reassessment triggers. |
| Notifications | `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all` | Operational alerts. |
| Audit | `GET /audit` | Traceable event history. |
| Surge | `POST /surge/start`, `POST /surge/stop`, `GET /surge/status` | 3x-volume scenario controls. |
| Devices | `POST /devices/register`, `GET /devices`, `GET /devices/{id}`, `POST /devices/{id}/simulate`, `POST /devices/{id}/disconnect` | Device simulation and vital ingestion. |
| Voice | `POST /voice/transcribe`, `POST /voice/extract-symptoms` | Backend-protected speech provider calls and symptom suggestions. |
| History | `GET /history/lookup` | Name-and-age history context lookup. |
| System | `GET /system/status`, `GET /system/config`, `PUT /system/reassessment-intervals` | Admin status and reassessment configuration. |
| Live updates | `WS /ws/queue` | Real-time queue broadcasts. |
| Health | `GET /health` | API, database, model, and voice-provider status. |

## ML and safety pipeline

- `app/services/assessment_service.py` orchestrates the full pipeline.
- `app/services/data_quality_service.py` computes completeness, missing fields, stale vitals, and conflicts.
- `app/services/clinical_rules.py` evaluates independent safety rules before the final recommendation.
- `app/ml/xgboost_engine.py` wraps the 14-feature XGBoost core engine when `ML_ENGINE=xgboost`.
- `app/ml/core_engine.py` loads the bundled model artifact and can use Gemini-compatible NLP extraction.
- `app/ml/mock_engine.py` provides a deterministic fallback when the configured ML path is unavailable.
- `app/services/decision_fusion.py` combines model output, rule output, age context, and data quality.
- `app/services/safety_gate.py` can escalate safety status but never downgrade it.

The XGBoost feature vector includes age, sex, heart rate, respiratory rate, SpO2, systolic BP, diastolic BP, temperature, time in queue, heart-rate delta, SpO2 delta, symptom-risk score, history-risk score, and missing-vital-sign count.

## Local development

### Docker workflow

```bash
cd vitalnode-backend
docker-compose up --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python seed.py
```

### Python workflow

```bash
cd vitalnode-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000
```

Create `.env` from `.env.example` and set real secrets through environment variables for any shared deployment.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Runtime environment. |
| `DATABASE_URL` | Async database URL used by the app. |
| `DATABASE_SYNC_URL` | Sync database URL used by Alembic. |
| `JWT_SECRET_KEY` | JWT signing secret. |
| `FRONTEND_URL` | Allowed frontend origin. |
| `DEMO_MODE` | Enables challenge demo routes when `true`. |
| `ML_ENGINE` | `mock` or `xgboost`. |
| `MODEL_PATH` | Optional model path for XGBoost. |
| `GEMINI_API_KEY` | Optional NLP extraction key. |
| `SPEECH_PROVIDER` | `mock`, `openai_whisper`, `assemblyai`, or another configured provider. |
| `SPEECH_API_KEY` | Backend-only speech provider secret. |
| `REASSESSMENT_CRITICAL_MIN` | Reassessment interval for critical acuity. |
| `REASSESSMENT_HIGH_MIN` | Reassessment interval for high acuity. |
| `REASSESSMENT_MODERATE_MIN` | Reassessment interval for moderate acuity. |
| `REASSESSMENT_LOW_MIN` | Reassessment interval for low acuity. |

## Tests

```bash
cd vitalnode-backend
pip install -r requirements.txt
pytest tests/ -v
```

The test suite uses an SQLite-compatible configuration and covers authentication, assessments, clinical rules, danger signs, data quality, queue behavior, safety-gate behavior, and vital validation.

## Project structure

```text
vitalnode-backend/
|-- app/
|   |-- main.py             # FastAPI app entry point
|   |-- core/               # Config, security, logging, exceptions
|   |-- db/                 # Database engine and sessions
|   |-- models/             # SQLAlchemy ORM models
|   |-- schemas/            # Pydantic schemas
|   |-- api/v1/             # REST and WebSocket routers
|   |-- services/           # Business logic
|   |-- ml/                 # ML interface, fallback engine, XGBoost adapter
|   |-- data/               # History lookup records
|   `-- workers/            # Background reassessment worker
|-- migrations/             # Alembic migrations
|-- tests/                  # Pytest suite
|-- seed.py                 # Challenge demo seeding script
|-- requirements.txt
|-- Dockerfile
`-- docker-compose.yml
```

VitalNode backend: AI-assisted triage, human-led decisions.
