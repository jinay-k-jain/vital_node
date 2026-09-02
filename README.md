# VitalNode

> Safety-gated, AI-assisted emergency triage prototype
> Accenture Innovation Challenge 2026

VitalNode is a deployed full-stack prototype for emergency department triage. It helps triage teams capture structured intake data, reason over vital signs and patient context, and produce an explainable ESI-based acuity recommendation. The system is designed for human-led care: the AI can recommend, but a clinical user must accept, override with a reason, or request reassessment before the active queue is updated.

Responsible-use notice: VitalNode is a competition prototype. It is not clinically validated, is not a medical device, and must not be used for real patient care, diagnosis, or treatment. The public deployment is for challenge evaluation only; do not enter real patient-identifiable information.

## Live submission links

| Resource | Link |
| --- | --- |
| Frontend demo | [https://vital-node.onrender.com/](https://vital-node.onrender.com/) |
| Backend API | [https://vitalnode-backend.onrender.com](https://vitalnode-backend.onrender.com) |
| Swagger / OpenAPI UI | [https://vitalnode-backend.onrender.com/docs](https://vitalnode-backend.onrender.com/docs) |
| ReDoc | [https://vitalnode-backend.onrender.com/redoc](https://vitalnode-backend.onrender.com/redoc) |
| Health check | [https://vitalnode-backend.onrender.com/health](https://vitalnode-backend.onrender.com/health) |

Render services may take a short time to wake after inactivity. If the first request is slow, wait a moment and retry.

### Demo access

| Role | Staff ID | Password |
| --- | --- | --- |
| Triage Nurse | `TN-0421` | `demo123` |
| Clinician | `CL-0112` | `demo123` |
| Administrator | `AD-0031` | `demo123` |

These credentials are provided only for the public challenge demo.

## The challenge

Emergency departments must continuously sort patients while information is incomplete, vital signs evolve, and arrival volume can change suddenly. A first-come-first-served workflow can hide clinical deterioration, make prioritisation difficult to explain, and leave audit gaps when staff are under pressure.

VitalNode demonstrates a safer decision-support workflow:

- Patients are arranged by acuity, safety status, reassessment urgency, and waiting time.
- Clinical safety rules run independently from the ML model.
- Recommendations include confidence, contributing factors, data quality, and safety-gate reasons.
- Staff control the queue: AI output remains pending until accepted or overridden.
- Reassessment timers and live WebSocket updates keep the queue current.
- Surge Mode demonstrates how the queue behaves during a 3x arrival-volume scenario.
- Login, AI prediction, decision, reassessment, configuration, and surge events are audit logged.

## Challenge Demo Walkthrough

1. Sign in at the live frontend with the triage nurse account.
2. Open Dashboard and search for patient records by name, ID, or complaint.
3. Create a New Assessment using the five-step intake flow: patient information, danger signs, vitals, chief complaint, and review.
4. Try a known patient name and age, such as `Rajesh Kumar` age `58`, to see the automatic history lookup banner.
5. Enter or record a chief complaint. Voice transcription is routed through the backend, and symptom chips remain suggestions until staff confirm them.
6. Review the AI Result page to inspect ESI acuity, confidence, model version, safety status, clinical rules, and top contributing factors.
7. Accept the recommendation, override it with a reason, or request reassessment. Only then does the active queue update.
8. Open Patient Queue to see ESI 1-2, ESI 3, and ESI 4-5 columns with safety flags, vitals, waiting time, and bed-assignment workflow.
9. Open Reassessment, Settings, Audit Log, Analytics, System Info, and Surge Mode to review operational behavior and traceability.

## Core Engine Test Output

The following run shows the standalone `VitalNode_ML/test_core.py` Gemini + XGBoost pipeline handling 15 surge scenarios, including clinical-rule overrides, pediatric escalation, missing-data handling, and NLP fallback behavior.

```text
venv) joy@joy:~/vital_node/VitalNode_ML$ python test_core.py
🏥 VITALNODE SURGE SIMULATION: 15-PATIENT GEMINI PIPELINE 🏥

Initiating 15-Patient Pipeline. Gemini API Rate Limit: 15 RPM (4.1s delay between calls)...
================================================================================

[1/15] 1. Cardiac Arrest (Immediate Danger)
Direct use of automatic function calling (AFC) in Models.generate_content is not recommended. Instead, we recommend to use AFC in Chat.send_message. Similarly, direct use of AFC in Models.generate_content_stream is not recommended. Instead, we recommend to use AFC in Chat.send_message_stream.
Extracted NLP:          Cardiac arrest (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 89.5%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Level 1 Immediate Danger Observed"]
AI Reasoning:           The patient is in active cardiac arrest with a heart rate of zero and no pulse, requiring immediate resuscitative intervention, while there is no medical history available to evaluate compounding risks.

[2/15] 2. Critical Respiratory Failure
Extracted NLP:          Severe respiratory distress (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 99.1%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Severe Hypoxia (SpO2 < 90%)"]
AI Reasoning:           The patient presents with critical respiratory failure characterized by severe hypoxia, cyanosis, and tachycardia, which is highly compounded by their history of severe COPD.

[3/15] 3. Extreme Tachycardia (Arrhythmia)
Extracted NLP:          Symptomatic tachycardia (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 99.3%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Critical Arrhythmia Risk (Extreme HR)"]
AI Reasoning:           The patient's extreme tachycardia of 195 bpm accompanied by dizziness indicates potential hemodynamic compromise, which is severely compounded by their documented history of SVT.

[4/15] 4. Neonatal Sepsis Trap (< 3 months)
Extracted NLP:          Febrile lethargy (Risk: 1)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 2 (Confidence: 72.7%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Neonate Fever Risk (Age <= 3mo, Temp >= 38\u00b0C)"]
AI Reasoning:           The combination of lethargy, fever, and marked tachycardia (HR 145) indicates a high-risk clinical state suggestive of systemic infection or sepsis, while the lack of available medical history provides no compounding risk factors.

[5/15] 5. Hypertensive Emergency (Stroke Risk)
Extracted NLP:          Acute severe headache (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 99.4%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Hypertensive Emergency (BP >= 180/120)"]
AI Reasoning:           A sudden-onset 'worst headache of life' accompanied by blurred vision in a patient with a history of hypertension is highly suspicious for a life-threatening neurological emergency such as a subarachnoid hemorrhage or hypertensive crisis.

[6/15] 6. Pediatric High Fever Risk
Extracted NLP:          Otalgia and fever (Risk: 2)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 2 (Confidence: 82.3%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Pediatric High Fever Risk (Temp >= 39\u00b0C)"]
AI Reasoning:           The patient presents with signs of acute otalgia and a high fever of 39.5°C, requiring urgent evaluation for potential otitis media while remaining hemodynamically stable with no known comorbidities.

[7/15] 7. Hypotension / Shock Risk
Extracted NLP:          Syncope and tachycardia (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 47.7%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Hypotension / Shock Risk (Sys BP < 90)"]
AI Reasoning:           The patient's syncope combined with significant tachycardia (HR 125) represents a high-risk cardiovascular or systemic issue requiring emergent evaluation, with no known historical comorbidities to compound the risk.

[8/15] 8. Extreme Hyperthermia
Extracted NLP:          Altered mental status (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 49.7%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Extreme Hyperthermia (Temp >= 40\u00b0C)"]
AI Reasoning:           The patient exhibits severe hyperthermia (Temp 40.2°C), tachycardia, and confusion, indicating a life-threatening heat stroke that requires immediate resuscitative cooling.

[9/15] 9. Abdominal Pain with History
Extracted NLP:          RLQ abdominal pain (Risk: 2)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 57.2%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with acute right lower quadrant pain and a low-grade fever, requiring urgent evaluation (ESI 3 equivalent) despite a history of appendectomy ruling out typical appendicitis.

[10/15] 10. Orthopedic Trauma
Extracted NLP:          Deformed upper extremity (Risk: 2)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 38.7%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a suspected extremity fracture requiring multiple emergency department resources including imaging, orthopedic consultation, and pain management, with mild tachycardia likely secondary to pain and no compounding historical risk factors.

[11/15] 11. Standard Adult Fever
Extracted NLP:          Fever and myalgia (Risk: 3)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 50.7%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with stable vital signs and a mild fever typical of a viral syndrome, with no reported medical history to complicate their condition.

[12/15] 12. Mild Allergic Reaction
Extracted NLP:          Localized allergic rash (Risk: 4)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 43.0%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a localized postprandial rash but has completely stable vital signs and no airway compromise, indicating a low-acuity, non-urgent allergic reaction.

[13/15] 13. Standard Pediatric Cold
Extracted NLP:          Cough and rhinorrhea (Risk: 4)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 60.1%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient exhibits mild upper respiratory symptoms with entirely stable vital signs and has no documented comorbidities, indicating a non-urgent status.

[14/15] 14. Minor Laceration
Extracted NLP:          Finger laceration (Risk: 4)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 74.4%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a minor finger laceration with controlled bleeding and completely stable vital signs, indicating a non-urgent condition with no known compounding history.

[15/15] 15. High Risk with Missing Data
NLP Fallback Triggered: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
Extracted NLP:          Unknown (Risk: 2)
ML Raw Prediction:      ESI 1
Final Fused Acuity:     ESI 1 (Confidence: 49.5%)
Safety Gate Action:     Verify Path: Incomplete Data & Uncertainty
AI Reasoning:           Standard protocol applied due to NLP timeout.

================================================================================
✅ SURGE SIMULATION COMPLETE.
```

## Key capabilities

| Capability | Current implementation |
| --- | --- |
| Deployed full-stack demo | React/Vite frontend and FastAPI backend are deployed on Render for challenge review. |
| Structured triage intake | Captures patient demographics, arrival mode, pregnancy status, danger signs, core vitals, AVPU, chief complaint, symptoms, and history context. |
| Safety-gated decisioning | Data quality checks, clinical safety rules, ML output, decision fusion, and a final safety gate run before staff review. |
| XGBoost-ready ML layer | Backend includes a 14-feature XGBoost adapter and bundled model artifact, with a deterministic fallback when a configured model is unavailable. |
| NLP-assisted context | Complaint and history text can be converted into bounded symptom-risk and history-risk scores using a Gemini-compatible workflow with caching and fallback behavior. |
| Human oversight | Staff can accept, override, or request reassessment. Overrides require a reason and preserve the original AI recommendation. |
| Dynamic priority queue | Server-side priority ordering combines acuity, safety flags, reassessment status, and waiting context. |
| Live updates | A FastAPI WebSocket endpoint broadcasts queue updates to connected frontend sessions. |
| Reassessment workflow | Configurable timers schedule follow-up review by acuity. A background worker checks overdue cases every minute and creates notifications. |
| Auditability | Major workflow events are persisted in an audit log and shown in the UI. |
| Surge readiness | Surge Mode creates a 3x-volume operational scenario while keeping safety rules, reassessment timers, and audit logging active. |
| Voice and device adapters | Backend supports voice transcription providers, keyword symptom extraction, and device vital-reading simulation routes. |
| Admin visibility | System Info and Settings expose model/configuration status, hospital settings, and reassessment interval controls. |

## System architecture

```text
React + TypeScript clinical dashboard
  Dashboard | Queue | New Assessment | AI Result | Reassessment
  Audit | Analytics | Surge | System Info | Settings
        |
        | REST + WebSocket
        v
FastAPI application
  JWT auth | role guards | API contracts | CORS | health checks
        |
        +--> PostgreSQL persistence
        |     patients | encounters | assessments | vitals
        |     recommendations | decisions | queue | audit | notifications
        |
        +--> Assessment pipeline
              intake + vitals + history
                    |
                    v
              data quality checks
                    |
                    v
              independent clinical rules
                    |
                    v
              ML inference adapter
              XGBoost engine or deterministic fallback
                    |
                    v
              decision fusion
                    |
                    v
              final safety gate
                    |
                    v
              staff accept | override | reassess
                    |
                    v
              queue update + audit event + WebSocket broadcast
```

## Safety model

VitalNode is deliberately designed as decision support, not autonomous triage.

1. Data quality checks identify missing critical vitals, missing context, stale vitals over 30 minutes, and invalid blood-pressure relationships.
2. Independent clinical rules flag safety signals such as severe hypoxia, low SpO2, hypotension, shock pattern, tachypnoea, altered consciousness, danger signs, anticoagulant-plus-trauma risk, pediatric tachycardia, low completeness, and zero-history altered consciousness.
3. ML inference estimates ESI acuity through the configured engine. The XGBoost path wraps `app/ml/core_engine.py`; the fallback engine keeps the workflow available when model loading or external services are unavailable.
4. Decision fusion takes the more conservative result when clinical rules indicate higher risk than the model. Low data completeness can cap confidence and mark the pathway conservative.
5. The safety gate can escalate `NORMAL` to `VERIFY` or `URGENT_REVIEW` for low confidence, poor or conflicting data, danger-sign mismatch, pediatric critical acuity, or model unavailability. It never downgrades an existing safety status.
6. Clinical users remain in control. A recommendation does not enter the live queue until accepted or overridden, and reassessment requests create follow-up workflow instead of silently changing acuity.

## AI and ML design

VitalNode maps Emergency Severity Index output to the queue-facing acuity labels used by the application:

| Model output | VitalNode acuity | Queue meaning |
| --- | --- | --- |
| ESI 1 | `CRITICAL` | Immediate, life-threatening concern |
| ESI 2 | `HIGH` | Emergent concern |
| ESI 3 | `MODERATE` | Urgent concern |
| ESI 4-5 | `LOW` | Lower-priority concern |

The model is one input to a safety-gated recommendation. It does not diagnose, treat, or make the final clinical decision.

### XGBoost feature set

The current XGBoost adapter builds a 14-feature vector from information available at triage time:

| Feature group | Features |
| --- | --- |
| Demographics | Age, encoded sex |
| Current observations | Heart rate, respiratory rate, SpO2, systolic BP, diastolic BP, temperature |
| Queue and reassessment context | Time in queue, heart-rate delta, SpO2 delta |
| NLP-derived context | Current symptom-risk score, history-risk score |
| Data reliability | Missing-vital-sign count |

For reassessments, the backend reads the latest two vital records and derives heart-rate and SpO2 deltas, allowing the model to receive a limited deterioration or improvement signal rather than only a single snapshot.

### NLP-assisted context

The backend can call a Gemini-compatible NLP workflow to transform complaint and history text into bounded fields:

- Primary symptom
- Symptom-risk score from `0` to `4`
- History-risk score from `0` to `3`
- One-sentence reasoning

The numeric scores are range-checked before entering the XGBoost model. Results are cached by complaint/history text, and reassessments reuse stored extraction when the complaint has not changed. If the external NLP call is unavailable, the backend continues with a conservative fallback.

### Explainability

The frontend receives and displays:

- Recommended acuity and ESI level
- Confidence percentage
- Model version and model status
- Data completeness
- Key reasons and top contributing factors
- Matched clinical safety rules
- Safety-gate status and safety flag
- Whether the conservative pathway was applied

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Zustand, Tailwind CSS, Recharts, Lucide |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, Structlog |
| Database | PostgreSQL for application state; SQLite-compatible test configuration |
| Authentication | JWT bearer authentication, bcrypt password hashing, backend-enforced role guards |
| ML/NLP | XGBoost, pandas, NumPy, Google GenAI/Gemini-compatible extraction, deterministic fallback engine |
| Live workflow | FastAPI WebSocket queue stream and asynchronous reassessment worker |
| Deployment | Render frontend and backend services; Docker support for backend/database development |

## Repository layout

```text
.
|-- README.md
|-- VitalNode_ML/
|   |-- core_engine.py                  # Standalone Groq + XGBoost prototype engine
|   |-- core_engine_gemini.py           # Gemini-oriented engine variant
|   |-- final_train.py                  # 14-feature XGBoost training script
|   |-- vitalnode_final_xgboost.json    # Model artifact
|   `-- test_core*.py                   # Prototype engine tests
|-- vitalnode/
|   |-- src/screens/                    # Dashboard, queue, assessment, audit, surge, settings, system views
|   |-- src/components/                 # Layout and shared clinical UI components
|   |-- src/lib/                        # REST and WebSocket clients
|   |-- src/store/                      # Zustand application state
|   `-- package.json
`-- vitalnode-backend/
    |-- app/api/v1/                     # REST and WebSocket routes
    |-- app/services/                   # Assessment, safety, queue, audit, surge, device, voice workflows
    |-- app/ml/                         # ML interface, fallback engine, XGBoost adapter, model artifact
    |-- app/models/                     # SQLAlchemy database models
    |-- app/schemas/                    # Pydantic request/response schemas
    |-- app/workers/                    # Reassessment scheduler
    |-- app/data/                       # Pre-loaded history lookup records
    |-- migrations/                     # Alembic schema migration
    |-- tests/                          # Backend unit/API tests
    |-- seed.py                         # Challenge demo users and records
    |-- Dockerfile
    `-- docker-compose.yml
```

## API surface

All application routes are exposed under `/api/v1`, except `/health`.

| Area | Representative routes | Purpose |
| --- | --- | --- |
| Authentication | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | Staff login and audit-aware logout. |
| Patient and assessment | `POST /patients/assess`, `GET /patients/search`, `GET /patients/{id}/timeline` | Submit intake, search records, and inspect timeline events. |
| AI workflow | `POST /assessments/{id}/predict`, `POST /assessments/{id}/decision`, `GET /assessments/{id}/quality` | Re-run the pipeline, save staff decisions, and view data quality. |
| Queue | `GET /queue`, `GET /queue/summary`, `POST /queue/{id}/complete` | View ordered cases, summary counts, and mark bed assignment. |
| Reassessment | `GET /reassessments`, `POST /reassessments/{id}` | List due cases and trigger reassessment. |
| Notifications and audit | `GET /notifications`, `POST /notifications/{id}/read`, `GET /audit` | Operational alerts and traceable event history. |
| Surge Mode | `POST /surge/start`, `POST /surge/stop`, `GET /surge/status` | Start, stop, and inspect the 3x-volume scenario. |
| System | `GET /system/status`, `GET /system/config`, `PUT /system/reassessment-intervals` | Admin status, configuration, and reassessment timer updates. |
| Devices and voice | `/devices/*`, `POST /voice/transcribe`, `POST /voice/extract-symptoms` | Device vital simulation and assisted intake. |
| History and live updates | `GET /history/lookup`, `WS /ws/queue` | History context lookup and real-time queue broadcasts. |
| Health | `GET /health` | API, database, model, and voice-provider health summary. |

Use the deployed Swagger UI for request and response schemas: [https://vitalnode-backend.onrender.com/docs](https://vitalnode-backend.onrender.com/docs).

## Configuration

The backend reads environment variables directly and also supports a local `.env` file. Render should provide production values through service environment settings.

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development` or `production`. |
| `DATABASE_URL` | Async PostgreSQL connection URL. |
| `DATABASE_SYNC_URL` | Sync PostgreSQL URL used by Alembic migrations. |
| `JWT_SECRET_KEY` | JWT signing secret; must be strong outside local development. |
| `FRONTEND_URL` | Allowed browser origin, set to `https://vital-node.onrender.com/` for the deployed frontend. |
| `DEMO_MODE` | Enables challenge scenario/reset endpoints when `true`. |
| `ML_ENGINE` | Selects `mock` or `xgboost`. |
| `MODEL_PATH` | Optional model path. If omitted, the backend XGBoost core looks for the bundled model artifact in `app/ml/`. |
| `GEMINI_API_KEY` | Optional key for NLP-assisted symptom and history extraction. |
| `SPEECH_PROVIDER` | `mock`, `openai_whisper`, `assemblyai`, or another configured provider. |
| `SPEECH_API_KEY` | Secret used only by the backend speech integration. |
| `REASSESSMENT_*_MIN` | Per-acuity reassessment intervals. |

Frontend deployment variables:

```env
VITE_API_URL=https://vitalnode-backend.onrender.com
VITE_WS_URL=wss://vitalnode-backend.onrender.com/api/v1/ws/queue
```

## Local development

The deployed Render links are the main path for challenge review. For local development, the backend can be run with Docker Compose and the frontend with Vite.

### Backend

```bash
cd vitalnode-backend
docker-compose up --build
docker-compose exec backend alembic upgrade head
docker-compose exec backend python seed.py
```

### Frontend

```bash
cd vitalnode
npm install
npm run dev
```

Vite prints the browser URL in the terminal. Keep local secrets in `.env` files and do not commit them.

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

Backend tests cover authentication, assessment creation, clinical rules, danger signs, data quality, queue ordering, safety-gate behavior, and vital validation.

## Current scope and roadmap

VitalNode is intentionally bounded as an innovation-challenge prototype. Before any real-world consideration, it would require:

- Clinical governance, expert review, and prospective validation.
- Calibration and monitoring for bias, drift, confidence, and patient-safety risk.
- Hospital integration work for EHR, ABDM/FHIR, devices, identity, and operational escalation.
- Production-grade secrets management, access control, logging policy, and security assessment.
- Privacy, consent, data-retention, and regulatory review.
- Usability testing with emergency-care staff.
- Durable multi-instance state for surge mode and other operational controls.

## Submission details

| Field | Details |
| --- | --- |
| Project | VitalNode |
| Frontend demo | [https://vital-node.onrender.com/](https://vital-node.onrender.com/) |
| Backend API | [https://vitalnode-backend.onrender.com](https://vitalnode-backend.onrender.com) |

VitalNode: AI-assisted triage. Human-led care.
