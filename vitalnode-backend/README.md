# VitalNode Backend

> **Prototype — Accenture Innovation Challenge 2026**  
> AI-assisted emergency triage system  
> ⚠️ NOT clinically validated. NOT for real patient care. Synthetic data only.

---

## Quick Start (Docker)

The fastest way to run everything:

```bash
cd vitalnode-backend
cp .env.example .env          # copy and review settings
docker-compose up --build     # starts PostgreSQL + backend
```

Then run migrations and seed:

```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python seed.py
```

API docs at: **http://localhost:8000/docs**

---

## Quick Start (Local)

### Requirements
- Python 3.12+
- PostgreSQL 14+

### Setup

```bash
cd vitalnode-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, DATABASE_SYNC_URL, JWT_SECRET_KEY
```

### Create the database

```bash
# In PostgreSQL:
createdb vitalnode_db
createuser vitalnode_user
# or use psql:
# CREATE DATABASE vitalnode_db;
# CREATE USER vitalnode_user WITH PASSWORD 'your_password';
# GRANT ALL PRIVILEGES ON DATABASE vitalnode_db TO vitalnode_user;
```

### Run migrations

```bash
alembic upgrade head
```

### Seed demo data

```bash
python seed.py
```

This creates:
- 3 demo users (see credentials below)
- 20 synthetic patients with full encounters, vitals, AI recommendations

### Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Demo Credentials

| Staff ID | Password | Role |
|---|---|---|
| TN-0421 | demo123 | Triage Nurse |
| CL-0112 | demo123 | Clinician |
| AD-0031 | demo123 | Administrator |

---

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | required |
| `DATABASE_SYNC_URL` | PostgreSQL sync URL (Alembic) | required |
| `JWT_SECRET_KEY` | JWT signing secret | required — change this! |
| `FRONTEND_URL` | Allowed CORS origin | `http://localhost:5173` |
| `ML_ENGINE` | `mock` or `xgboost` | `mock` |
| `SPEECH_PROVIDER` | `mock`, `openai_whisper`, etc. | `mock` |
| `DEMO_MODE` | Enables `/api/v1/demo/*` endpoints | `true` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` | `INFO` |

---

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
- **Health check**: http://localhost:8000/health

---

## API Overview

All endpoints are prefixed `/api/v1/`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Login, receive JWT |
| GET | `/auth/me` | Any | Current user info |
| POST | `/auth/logout` | Any | Record logout |
| POST | `/patients/assess` | Nurse/Clinician | Create patient + run AI |
| GET | `/patients/search?q=` | Any | Search patients |
| GET | `/patients/{id}/timeline` | Any | Patient event timeline |
| POST | `/assessments/{id}/predict` | Nurse/Clinician | Re-run AI pipeline |
| POST | `/assessments/{id}/decision` | Nurse/Clinician | Accept / Override / Reassess |
| GET | `/assessments/{id}/quality` | Any | Data quality report |
| GET | `/queue` | Any | Priority-ordered queue |
| GET | `/queue/summary` | Any | Department summary stats |
| GET | `/reassessments` | Any | Overdue reassessments |
| POST | `/reassessments/{id}` | Nurse/Clinician | Trigger reassessment |
| GET | `/notifications` | Any | List notifications |
| POST | `/notifications/{id}/read` | Any | Mark as read |
| POST | `/notifications/read-all` | Any | Mark all read |
| GET | `/audit` | Any | Audit log |
| POST | `/surge/start` | Nurse/Clinician | Activate 3× surge |
| POST | `/surge/stop` | Nurse/Clinician | Deactivate surge |
| GET | `/surge/status` | Any | Current surge state |
| POST | `/devices/register` | Nurse/Clinician | Register device |
| GET | `/devices` | Any | List devices |
| POST | `/devices/{id}/simulate` | Nurse/Clinician | Simulate vital reading |
| POST | `/devices/{id}/disconnect` | Nurse/Clinician | Simulate disconnect |
| POST | `/voice/transcribe` | Nurse/Clinician | Transcribe audio |
| POST | `/voice/extract-symptoms` | Nurse/Clinician | Extract symptoms from text |
| GET | `/system/status` | **Admin only** | Detailed system status |
| GET | `/system/config` | **Admin only** | Hospital configuration |
| GET | `/demo/scenarios` | Any (DEMO_MODE) | List demo scenarios |
| POST | `/demo/reset` | Any (DEMO_MODE) | Reset demo data |
| POST | `/demo/simulate-deterioration/{id}` | Any (DEMO_MODE) | Simulate deterioration |
| GET | `/health` | None | API health check |

---

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio httpx aiosqlite

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v
pytest tests/test_clinical_rules.py -v
pytest tests/test_safety_gate.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

Tests use **in-memory SQLite** — no PostgreSQL needed to run the test suite.

---

## Architecture

```
NURSE INPUT
     ↓
POST /api/v1/patients/assess
     ↓
PatientService → Patient + Encounter + Assessment + Vital + QueueEntry
     ↓
AssessmentService.run_ai_assessment()
     ├─ compute_data_quality()
     ├─ evaluate_clinical_rules()   ← INDEPENDENT from ML
     ├─ ml_engine.predict()         ← MockMLEngine (or XGBoost later)
     ├─ decision_fusion.fuse()      ← Combines ML + rules + quality
     └─ safety_gate.run_safety_gate() ← Final safety check
     ↓
AIRecommendation stored (immutable)
Encounter priority updated
Reassessment timer set
Audit event recorded
     ↓
NURSE DECISION → POST /api/v1/assessments/{id}/decision
     ↓
NurseDecision stored (AI recommendation NEVER deleted)
Audit event recorded
```

### Key Design Principles
- **Safety gate can only escalate**, never downgrade
- **Clinical rules are independent from ML** — work even if ML is down
- **All vitals stored as new rows** — enables deterioration detection
- **AI recommendations are immutable** — override stores both AI + nurse decision
- **Audit log is insert-only** — no updates or deletes ever
- **Missing data is explicit** — never imputed or assumed normal

---

## Plugging in Real XGBoost

1. Set `ML_ENGINE=xgboost` in `.env`
2. Set `MODEL_PATH=/path/to/model.json`
3. `pip install xgboost`
4. Implement `predict()` in `app/ml/xgboost_engine.py`
5. Map `MLFeatures` dataclass → model feature vector
6. Nothing else changes

The `MLFeatures` dataclass is the contract between the pipeline and the model.

---

## Connecting the Frontend

The frontend currently uses **local Zustand state only** (no API calls).

To connect it to this backend:

1. Add an API client (axios or fetch) to the frontend
2. Replace `appStore.ts` actions with API calls:
   - `login()` → `POST /api/v1/auth/login`
   - `addPatient()` + `runAI` → `POST /api/v1/patients/assess`
   - `acceptRecommendation()` → `POST /api/v1/assessments/{id}/decision`
   - `overrideAcuity()` → `POST /api/v1/assessments/{id}/decision`
   - `triggerReassessment()` → `POST /api/v1/reassessments/{id}`
   - Queue → `GET /api/v1/queue`
   - Notifications → `GET /api/v1/notifications`
   - Audit → `GET /api/v1/audit`

The backend response shapes match the existing frontend types exactly.

---

## Limitations

This is a competition prototype. Before any real deployment:

- The ML model requires clinical validation
- Clinical rules require review by qualified medical staff
- Full security audit is required
- Privacy/legal assessment under Indian DPDP Act is required
- ABDM/FHIR integration requires ABDM developer registration
- Pediatric thresholds require separate clinical validation
- No horizontal scaling (single-process only in current form)
- Surge state is in-memory (resets on restart)

---

## Project Structure

```
vitalnode-backend/
├── app/
│   ├── main.py              ← FastAPI app entry point
│   ├── core/                ← Config, security, logging, exceptions
│   ├── db/                  ← Database engine and session
│   ├── models/              ← SQLAlchemy ORM models (11 tables)
│   ├── schemas/             ← Pydantic input/output schemas
│   ├── api/v1/              ← All API routers (14 files)
│   ├── services/            ← Business logic (12 services)
│   ├── ml/                  ← ML interface, mock engine, XGBoost stub
│   └── workers/             ← Background reassessment timer worker
├── migrations/              ← Alembic database migrations
├── tests/                   ← pytest test suite (8 test files)
├── seed.py                  ← Demo data seeder
├── requirements.txt
├── alembic.ini
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── BACKEND_IMPLEMENTATION_PLAN.md
└── README.md
```

---

*VitalNode — Prototype for Accenture Innovation Challenge 2026*  
*AI-assisted triage. Human-led care.*
