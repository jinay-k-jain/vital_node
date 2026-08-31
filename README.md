# VitalNode

> **Safety-gated, AI-assisted emergency triage prototype**  
> *Accenture Innovation Challenge 2026*

VitalNode helps emergency-department teams prioritise **synthetic** patient cases under time pressure. It combines structured intake, vital signs, data-quality checks, independent clinical safety rules, and an interchangeable ML inference layer to produce an explainable acuity recommendation. The clinician remains the decision-maker: they can accept, override with a reason, or request reassessment, and every significant action is audit logged.

> **Responsible-use notice:** VitalNode is a competition prototype using synthetic data. It is **not** clinically validated, is not a medical device, and must never be used for real patient care, diagnosis, or treatment decisions.

## The challenge

Emergency departments must continuously sort patients while information is incomplete, vital signs evolve, and the number of arrivals can suddenly rise. A purely first-come-first-served process can hide deterioration and makes prioritisation hard to review.

VitalNode demonstrates a human-in-the-loop workflow that makes prioritisation visible, safety-conscious, and traceable:

- Produces a queue ordered by patient acuity.
- Independently evaluates data quality and clinical safety signals.
- Shows confidence, contributing factors, and verification guidance.
- Prevents an AI recommendation from changing the active queue until clinical staff act.
- Supports reassessment deadlines and live queue updates.
- Simulates a deterministic 3× arrival surge without external API usage.

## Key capabilities

| Capability | Implementation in this prototype |
| --- | --- |
| Structured triage intake | Captures demographics, arrival mode, pregnancy status, complaint, symptoms, history, danger signs, and vital signs. |
| Safety-gated decisioning | Clinical rules run independently of model inference; decision fusion and a final safety gate can escalate but never silently reduce a safety status. |
| Explainable recommendation | Returns acuity, confidence, model status/version, top factors, matched rules, data completeness, and safety reasons. |
| Human oversight | Triage staff can accept, override (with a mandatory reason), or request reassessment. The original AI recommendation is retained. |
| Data-quality awareness | Detects missing, stale, invalid, and conflicting entries; low completeness reduces confidence and triggers a conservative pathway. |
| Continuous triage | A background worker checks reassessment deadlines every minute and broadcasts queue updates over WebSocket. |
| Auditability | Login, prediction, clinician decision, reassessment, configuration, and surge events are persisted in the audit log. |
| Surge readiness demo | Starting surge mode adds twice the normal active volume, yielding exactly 3× the baseline queue. |
| Voice-assisted intake | Supports mock transcription and configurable speech-to-text providers; extracted symptoms remain suggestions for staff confirmation. |

## System architecture

```text
                         ┌─────────────────────────────────────────┐
                         │ React + TypeScript clinical dashboard   │
                         │ queue · intake · result · audit · surge │
                         └──────────────────┬──────────────────────┘
                                            │ REST + WebSocket
                         ┌──────────────────▼──────────────────────┐
                         │ FastAPI application                     │
                         │ JWT auth · role guards · API contracts  │
                         └──────────────────┬──────────────────────┘
                                            │
  Intake + vitals ──► Data quality ──► Clinical rules ──► ML engine
                                            │                   │
                                            └──── Decision fusion ◄┘
                                                         │
                                                  Final safety gate
                                                         │
                                              Recommendation + audit event
                                                         │
                                  Clinician accept / override / reassess
                                                         │
                          PostgreSQL queue + notifications + WebSocket update
```

### Safety model

VitalNode is deliberately designed as decision support, not autonomous triage.

1. **Data quality:** Checks for missing vital/context fields, stale vitals (over 30 minutes), invalid blood-pressure relationships, and conflicting data.
2. **Independent clinical rules:** Illustrative rules identify signals including severe hypoxaemia, hypotension, shock pattern, altered consciousness, danger signs, paediatric tachycardia, low data completeness, and zero-history altered consciousness.
3. **ML inference:** The backend uses a deterministic mock engine by default. An XGBoost adapter can be selected when a model path is configured.
4. **Decision fusion:** If rules indicate a more severe acuity than the model, the more conservative acuity wins. Poor completeness caps confidence and applies conservative handling.
5. **Safety gate:** The final gate can raise `NORMAL` to `VERIFY` or `URGENT_REVIEW` because of low confidence, critical/conflicting data, danger-sign mismatch, paediatric critical acuity, or model unavailability. It never downgrades the existing safety level.
6. **Clinician decision:** Recommendations are pending until a qualified user accepts or overrides them. Overrides preserve the AI result and rationale in the audit trail.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Zustand, Tailwind CSS, Recharts, Lucide |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy async, Alembic, Structlog |
| Data | PostgreSQL 16 (Docker Compose); SQLite-compatible test configuration |
| Security | JWT bearer authentication, bcrypt password hashing, backend-enforced role guards |
| ML/NLP | Pluggable mock or XGBoost engine; optional Gemini-compatible symptom extraction with safe fallback/caching |
| Live workflow | FastAPI WebSocket queue stream and asynchronous reassessment worker |
| Packaging | Docker and Docker Compose for the backend and database |

## AI and ML design

### What the model does

VitalNode’s ML layer estimates a patient’s triage category on an **Emergency Severity Index (ESI) 1–5 scale**. The backend maps this to the user-facing queue:

| Model output | VitalNode acuity | Meaning in this prototype |
| --- | --- | --- |
| ESI 1 | `CRITICAL` | Immediate, life-threatening concern |
| ESI 2 | `HIGH` | Emergent concern |
| ESI 3 | `MODERATE` | Urgent concern |
| ESI 4–5 | `LOW` | Lower-priority concern |

The model is **one input to a safety-gated recommendation**. It does not make the final clinical decision and cannot override the independent safety logic.

### Inference options

| Engine | When used | Behaviour |
| --- | --- | --- |
| `mock` (default) | Local demo and development | Deterministic threshold-based model simulation, explicitly returned as `MODEL_STATUS=MOCK`. It keeps the competition demo reproducible without requiring external services. |
| `xgboost` | When `ML_ENGINE=xgboost` and a model artifact is available | Loads the supplied XGBoost model JSON and returns the predicted ESI class, probability-derived confidence, and generated explanation factors. |
| Rules-only fallback | When a configured ML engine cannot serve a prediction | Uses the clinical-rule pathway with reduced confidence and verification-oriented handling; the model status is exposed as unavailable. |

### XGBoost feature set

The configured production-style inference adapter builds a 14-feature vector from information available at triage time. Missing vital signs remain missing values for model handling and are also counted explicitly.

| Feature group | Features |
| --- | --- |
| Demographics | Age, encoded sex |
| Current observations | Heart rate, respiratory rate, SpO₂, systolic BP, diastolic BP, temperature |
| Queue and trend context | Time in queue, heart-rate change, SpO₂ change |
| NLP-derived context | Current symptom-risk score, history-risk score |
| Data reliability | Missing-vital-sign count |

For reassessments, the system derives heart-rate and SpO₂ deltas from the latest two vital records. This lets the model receive a limited deterioration/improvement signal rather than only a single snapshot.

### NLP-assisted context, with safe fallbacks

For normal XGBoost assessments, an optional Gemini-compatible call transforms the free-text complaint and available history into four tightly bounded fields: a primary symptom, symptom-risk score (`0–4`), history-risk score (`0–3`), and one-sentence reasoning. The numeric scores are range-checked before entering the model.

The NLP result is cached by complaint/history and stored with the assessment, so unchanged reassessments do not make repeat requests. If no API key is configured or the request fails, VitalNode returns a conservative fallback extraction and continues the safety workflow. Synthetic surge cases always use local deterministic keyword extraction, ensuring the 3× demo is repeatable and does not consume API quota.

### Confidence and explainability

- XGBoost confidence is the highest class probability, displayed as a percentage.
- The mock engine emits deterministic confidence based on available observations and the applied pathway.
- Low data completeness caps confidence at 55% in decision fusion; confidence below 50% escalates the safety status to at least `VERIFY`.
- The user interface receives top contributing factors, matched clinical rules, data-quality findings, safety-gate reasons, model version, and model status alongside the recommendation.

### Why this is safer than model-only triage

The system separates statistical inference from safety rules. For example, rules can escalate for severe oxygen desaturation, hypotension, shock pattern, altered consciousness, immediate danger signs, or vulnerable paediatric/zero-history presentations—even if model confidence is low or the model output suggests a lower acuity. This conservative fusion policy is intentional: it prioritises review over silent under-triage in uncertain cases.

## Repository layout

```text
.
├── README.md
├── core_engine.py                       # Standalone ML/NLP prototype engine
├── vitalnode/                           # React frontend
│   ├── src/screens/                     # Dashboard, queue, assessment, audit, surge, settings
│   ├── src/components/                  # Layout and shared clinical UI components
│   ├── src/lib/                         # REST and WebSocket clients
│   ├── src/store/                       # Zustand application state
│   └── package.json
└── vitalnode-backend/                   # FastAPI backend
    ├── app/api/v1/                      # Authenticated REST and WebSocket routes
    ├── app/services/                    # Assessment, safety, queue, audit, surge workflows
    ├── app/ml/                          # ML interface, mock engine, XGBoost adapter/model assets
    ├── app/models/                      # SQLAlchemy database models
    ├── app/workers/                     # Reassessment scheduler
    ├── migrations/                      # Alembic schema migration
    ├── tests/                           # Backend unit/API tests
    ├── seed.py                          # Demo users and synthetic patient records
    ├── Dockerfile
    └── docker-compose.yml
```

## Quick start

### Prerequisites

- Docker Desktop with Docker Compose
- Node.js 20+ and npm

### 1. Start PostgreSQL and the API

```bash
cd vitalnode-backend
docker-compose up --build
```

In a second terminal, initialise the schema and load the competition demo data:

```bash
cd vitalnode-backend
docker-compose exec backend alembic upgrade head
docker-compose exec backend python seed.py
```

The API runs at `http://localhost:8000`.

- Interactive API documentation: `http://localhost:8000/docs`
- OpenAPI document: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

### 2. Start the frontend

```bash
cd vitalnode
npm install
npm run dev
```

Open the Vite URL displayed in the terminal, normally `http://localhost:5173`.

### Optional frontend environment

The defaults target the local backend. To point at another deployment, create `vitalnode/.env.local`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/api/v1/ws/queue
```

### Demo accounts

| Role | Staff ID | Password |
| --- | --- | --- |
| Triage Nurse | `TN-0421` | `demo123` |
| Clinician | `CL-0112` | `demo123` |
| Administrator | `AD-0031` | `demo123` |

These are seeded demonstration accounts only; do not reuse these credentials outside the local prototype.

## Demo walkthrough

1. Sign in as `TN-0421`.
2. Open **Patient Queue** to review the prioritised synthetic patients.
3. Select a patient to inspect the AI result: acuity, confidence, data completeness, factors, rules, and safety badge.
4. Submit an **accept** decision or an **override** with a reason to show clinician control.
5. Open **Audit Log** to show that prediction and decision events are preserved.
6. Open **Settings**, adjust the reassessment intervals, and save them. Active queued encounters are rescheduled and the change is audited.
7. Open **Surge Mode** and activate the 3× simulation. With the supplied seed, 20 normal active cases generate 40 synthetic arrivals for 60 total cases.
8. Use **Reassessment** or wait for the scheduled worker to demonstrate follow-up alerts and a refreshed queue.

## API surface

All application endpoints are prefixed with `/api/v1`; most require a JWT bearer token returned by `POST /auth/login`.

| Area | Representative routes | Purpose |
| --- | --- | --- |
| Authentication | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | Staff session and audit-aware logout. |
| Patient and assessment | `POST /patients/assess`, `GET /patients/search`, `GET /patients/{id}/timeline` | Submit intake, find patients, and inspect timelines. |
| AI workflow | `POST /assessments/{id}/predict`, `POST /assessments/{id}/decision`, `GET /assessments/{id}/quality` | Run the pipeline, record clinical decision, and view data quality. |
| Queue/reassessment | `GET /queue`, `GET /queue/summary`, `POST /queue/{id}/complete`, `GET /reassessments`, `POST /reassessments/{id}` | View/complete prioritised cases and manage reassessment. |
| Operations | `GET /notifications`, `GET /audit`, `POST /surge/start`, `POST /surge/stop`, `GET /surge/status` | Operational notifications, audit, and deterministic surge simulation. |
| Administration | `GET /system/status`, `GET /system/config`, `PUT /system/reassessment-intervals` | System visibility and reassessment configuration. |
| Devices and voice | `/devices/*`, `POST /voice/transcribe`, `POST /voice/extract-symptoms` | Simulated device readings and assisted intake. |
| Demo and live updates | `/demo/*` (demo mode), `WS /ws/queue` | Reset/deterioration scenarios and real-time queue broadcasts. |

Refer to the running Swagger UI for request and response schemas.

## Configuration

The backend reads environment variables (and, for local execution, `vitalnode-backend/.env`). Docker Compose supplies safe development defaults. Never use the defaults in a real deployment.

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | Local PostgreSQL URL | Async application database connection. |
| `DATABASE_SYNC_URL` | Local PostgreSQL URL | Sync connection used by Alembic. |
| `JWT_SECRET_KEY` | Insecure development value | Must be replaced with a strong secret outside local demo use. |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed frontend origin. |
| `DEMO_MODE` | `true` | Enables demo-only endpoints. |
| `ML_ENGINE` | `mock` | Selects `mock` or `xgboost`. |
| `MODEL_PATH` | Empty | Model path required for the XGBoost path. |
| `GEMINI_API_KEY` | Empty | Optional key for the NLP-enabled model workflow. |
| `SPEECH_PROVIDER` | `mock` | `mock`, `openai_whisper`, `assemblyai`, or other configured option. |
| `SPEECH_API_KEY` | Empty | Secret used only by the backend speech integration. |

To enable the XGBoost adapter locally, configure a valid model file and restart the backend:

```env
ML_ENGINE=xgboost
MODEL_PATH=/absolute/path/to/vitalnode_final_xgboost.json
GEMINI_API_KEY=your_optional_key
```

If XGBoost or an external NLP service is unavailable, the assessment flow falls back to safe mock/rules-based handling and exposes the model status to the user.

## Reassessment and surge behaviour

### Reassessment

Default reassessment intervals are 5 minutes for `CRITICAL`, 15 for `HIGH`, 30 for `MODERATE`, and 60 for `LOW`. Administrators can set each interval between 1 and 180 minutes. The background worker runs every 60 seconds, checks overdue waiting encounters, creates notifications as required, and broadcasts a queue refresh.

The reassessment feature considers the latest and previous vital signs so the ML feature set can capture changes in heart rate and oxygen saturation.

### 3× surge simulation

Surge mode counts active non-surge encounters, then creates exactly twice that number of deterministic synthetic arrivals. These cases travel through the same assessment, clinical-rule, safety-gate, queue, and audit paths. Extra surge cases use local deterministic symptom extraction rather than consuming Gemini/API calls. Stopping surge mode marks active synthetic surge encounters as discharged.

## Validation

Frontend production build:

```bash
cd vitalnode
npm run build
```

Backend test suite:

```bash
cd vitalnode-backend
pip install -r requirements.txt
pytest tests/ -v
```

The frontend production build has been verified in this workspace. The backend test suite covers authentication, assessments, clinical rules, danger signs, data quality, queue ordering, safety-gate behaviour, and vital validation. Ensure all packages from `requirements.txt` are installed in the Python environment before running it.

## Current scope and roadmap

The system is intentionally bounded as a competition prototype. Before any real-world consideration, it would require:

- Clinical governance and validation with representative, ethically governed datasets.
- Expert review and calibration of every triage threshold and safety rule.
- Bias, drift, calibration, and patient-safety monitoring.
- Durable configuration/state for multi-instance deployment rather than prototype in-memory state.
- Production secrets management, hardened deployment, access management, and security assessment.
- Consent, privacy, data-retention, regulatory, and hospital-integration work.
- Usability testing with emergency-care staff and a formal incident/escalation process.

No real patient records are included in this repository.

## Submission details

| Field | Details |
| --- | --- |
| Challenge | Accenture Innovation Challenge 2026 |
| Project | VitalNode |
| Team name | `<add team name>` |
| Team members | `<add names and responsibilities>` |
| Demo video | `<add link>` |
| Presentation | `<add link>` |
