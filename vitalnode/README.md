# VitalNode Frontend

React + TypeScript frontend for the VitalNode emergency triage prototype.

Live demo: [https://vital-node.onrender.com/](https://vital-node.onrender.com/)

## What it includes

- Secure staff login against the FastAPI backend.
- Dashboard search by patient name, patient ID, or complaint.
- Five-step new assessment flow with demographics, danger signs, vitals, chief complaint, symptom suggestions, history lookup, and data-completeness review.
- AI result screen with acuity, ESI label, confidence, top factors, clinical rules, and safety-gate status.
- Staff accept, override, and reassess actions.
- Priority queue grouped into ESI 1-2, ESI 3, and ESI 4-5 columns.
- Reassessment queue with due and overdue timers.
- Audit log, analytics, surge-mode, system-info, and settings screens.
- WebSocket queue updates from the backend.

## Backend connection

The deployed frontend points at:

```env
VITE_API_URL=https://vitalnode-backend.onrender.com
VITE_WS_URL=wss://vitalnode-backend.onrender.com/api/v1/ws/queue
```

For another environment, set these variables before building.

## Demo access

| Role | Staff ID | Password |
| --- | --- | --- |
| Triage Nurse | `TN-0421` | `demo123` |
| Clinician | `CL-0112` | `demo123` |
| Administrator | `AD-0031` | `demo123` |

## Development

```bash
npm install
npm run dev
```

## Production build

```bash
npm run build
```

The generated static assets are emitted to `dist/`.
