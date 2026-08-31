import React from 'react';
import { Cpu, Database, Shield, AlertTriangle, Server, Globe, GitBranch } from 'lucide-react';

export function SystemInfoScreen() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto w-full">
      <div>
        <h1 className="text-xl font-bold text-slate-900">System Information</h1>
        <p className="text-sm text-slate-500 mt-0.5">Model details, architecture, and system limitations.</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-800 leading-relaxed">
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-bold text-amber-900 mb-1">Important Disclaimer</p>
            <p>VitalNode is a prototype for the Accenture Innovation Challenge 2026. It is not clinically validated, not WHO certified, and not intended for actual patient care. The AI model assists with prioritisation only — it does not diagnose, treat, or replace clinical judgment.</p>
          </div>
        </div>
      </div>

      {/* ML Model */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Cpu size={16} className="text-violet-600" />
          <h2 className="text-sm font-bold text-slate-800">ML Model</h2>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-slate-500">Model type: </span><span className="font-semibold text-slate-800">XGBoost</span></div>
          <div><span className="text-slate-500">Version: </span><span className="font-semibold text-slate-800">v1.0</span></div>
          <div><span className="text-slate-500">Training dataset: </span><span className="font-semibold text-slate-800">Research dataset (MIMIC-derived)</span></div>
          <div><span className="text-slate-500">Purpose: </span><span className="font-semibold text-slate-800">Acuity risk estimation</span></div>
          <div><span className="text-slate-500">Output: </span><span className="font-semibold text-slate-800">Acuity class + probabilities</span></div>
          <div><span className="text-slate-500">Explainability: </span><span className="font-semibold text-slate-800">SHAP values (feature contributions)</span></div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-100">
          <div className="text-xs font-semibold text-slate-600 mb-2">Input Features</div>
          <div className="flex flex-wrap gap-1.5">
            {['SpO₂', 'Heart Rate', 'Respiratory Rate', 'Systolic BP', 'Diastolic BP', 'Temperature', 'AVPU', 'Age', 'Sex', 'Chief Complaint (NLP)', 'Danger Signs', 'Symptom Set', 'Medical History'].map(f => (
              <span key={f} className="text-xs bg-violet-50 border border-violet-200 text-violet-800 px-2 py-0.5 rounded-full">{f}</span>
            ))}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-100">
          <div className="text-xs font-semibold text-slate-600 mb-2">Known Limitations</div>
          <ul className="text-xs text-slate-600 space-y-1 list-disc list-inside">
            <li>Model trained on research data, not validated for Indian ED population.</li>
            <li>Performance may vary with rare presentations or atypical demographics.</li>
            <li>Model confidence does not equal clinical certainty.</li>
            <li>Missing data reduces confidence — model does not fabricate values.</li>
            <li>Pediatric thresholds require separate clinical validation before deployment.</li>
            <li>Model does not diagnose disease — it estimates acuity risk only.</li>
          </ul>
        </div>
      </div>

      {/* Clinical Rules */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={16} className="text-blue-600" />
          <h2 className="text-sm font-bold text-slate-800">Clinical Safety Rule Engine</h2>
        </div>
        <p className="text-xs text-slate-600 mb-3 leading-relaxed">
          The clinical safety rule engine operates independently from the ML model. Rules are applied before and after the ML prediction. The Safety Gate combines both outputs.
        </p>
        <div className="space-y-2 text-xs">
          {[
            'Critical oxygenation threshold (SpO₂ < 90%)',
            'Hemodynamic instability pattern (BP + HR)',
            'Respiratory distress indicators',
            'Altered consciousness escalation',
            'Danger sign triggers',
            'Ambiguous presentation + low confidence → conservative',
            'Missing critical vitals → reduced confidence',
            'Stale measurements → verification required',
            'Pediatric pathway — age-appropriate thresholds',
            'Anticoagulant + trauma pattern',
            'Atypical cardiac presentation in females',
            'Zero-history + altered consciousness → conservative',
          ].map(rule => (
            <div key={rule} className="flex items-center gap-2 text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
              {rule}
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-3">
          Rules are illustrative for prototype purposes. Production rules must be defined and validated by qualified clinical staff.
        </p>
      </div>

      {/* Architecture */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Server size={16} className="text-slate-600" />
          <h2 className="text-sm font-bold text-slate-800">System Architecture</h2>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 font-mono text-xs text-slate-700 leading-relaxed">
          <pre>{`PATIENT
 ↓
Data Sources
  ├─ Medical Device Gateway (HL7/FHIR)
  ├─ Manual Nurse Input
  ├─ Voice → NLP → Symptoms
  └─ Hospital EHR (ABDM Integration)
 ↓
Data Normalisation & Validation
 ↓
Data Quality Assessment
 ↓
Age & Context Pathway Selection
 ↓
┌──────────────────────┐   ┌──────────────────────┐
│  WHO-aligned Rules   │   │  XGBoost ML Engine   │
│  (Safety rules)      │   │  (Acuity risk)        │
└──────────┬───────────┘   └──────────┬───────────┘
           └──────────────────────────┘
                          ↓
                  Decision Fusion Layer
                          ↓
                    Safety Gate
                          ↓
                  AI Recommendation
                    + Confidence
                    + Explainability (SHAP)
                    + Safety Status
                          ↓
                      NURSE REVIEW
                    Accept / Override / Reassess
                          ↓
                  Dynamic Priority Queue
                          ↓
                  Reassessment Monitor
                    (Timer / Vital / Observation)
                          ↓
                      AI runs again
                          ↓
                   Audit Log (immutable)`}</pre>
        </div>
      </div>

      {/* Privacy */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={16} className="text-green-600" />
          <h2 className="text-sm font-bold text-slate-800">Privacy & Security</h2>
        </div>
        <div className="text-xs text-slate-600 space-y-2 leading-relaxed">
          <p>VitalNode is designed with India-focused privacy and security principles, including alignment with the Digital Personal Data Protection (DPDP) framework.</p>
          <div className="grid grid-cols-2 gap-2 mt-3">
            {[
              'Staff authentication', 'Role-based access control', 'Audit logging',
              'Encrypted communications', 'Data minimisation', 'Synthetic data in prototype',
              'No PII in logs', 'FHIR-compatible data structures'
            ].map(item => (
              <div key={item} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                {item}
              </div>
            ))}
          </div>
          <p className="text-slate-400 mt-2">
            Full DPDP compliance has not been assessed for this prototype. Production deployment requires qualified legal and security review.
          </p>
        </div>
      </div>

      {/* ABDM/FHIR */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Globe size={16} className="text-blue-600" />
          <h2 className="text-sm font-bold text-slate-800">ABDM / FHIR Integration</h2>
        </div>
        <p className="text-xs text-slate-600 mb-3 leading-relaxed">
          VitalNode is designed for integration with Indian hospital systems via the ABDM (Ayushman Bharat Digital Mission) integration layer and FHIR-compatible data structures.
        </p>
        <div className="bg-slate-50 rounded-lg p-4 font-mono text-xs text-slate-700 leading-relaxed">
          <pre>{`Hospital EHR
    ↓
FHIR / ABDM Integration Adapter
    ↓
VitalNode API (FastAPI)
    ↓
Patient Service → Assessment Service → ML Service
    ↓
Authorised hospital workflow`}</pre>
        </div>
        <p className="text-xs text-slate-400 mt-2">ABDM integration is simulated in this prototype. Live integration requires ABDM developer registration and compliance review.</p>
      </div>
    </div>
  );
}
