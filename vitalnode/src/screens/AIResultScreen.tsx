import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { SafetyBadge } from '../components/shared/SafetyBadge';
import { ConfidenceBar } from '../components/shared/ConfidenceBar';
import { OverrideModal } from '../components/OverrideModal';
import {
  Info, Check, X, RefreshCw, ChevronDown, ChevronUp,
  ShieldAlert, Baby, ArrowRight, Cpu,
} from 'lucide-react';
import clsx from 'clsx';
import { Patient } from '../types';
import { acuityConfig } from '../utils/acuity';

export function AIResultScreen() {
  const {
    patients, selectedPatientId,
    acceptRecommendation, setCurrentView,
    user, triggerReassessment,
  } = useAppStore();
  const pendingPatient = (useAppStore.getState() as any)._pendingPatient;

  // Keep a stable reference to the patient so the screen never goes blank
  const stablePatient = useRef<Patient | undefined>(undefined);
  const livePatient = patients.find(p => p.id === selectedPatientId)
    || (pendingPatient?.id === selectedPatientId ? pendingPatient : undefined);
  if (livePatient) stablePatient.current = livePatient;

  const patient = stablePatient.current;

  const [showExplanation, setShowExplanation] = useState(false);
  const [showOverride, setShowOverride] = useState(false);
  const [accepted, setAccepted] = useState(false);

  if (!patient) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <p className="text-sm text-slate-400">No patient selected. Please select a patient from the queue.</p>
        <button onClick={() => setCurrentView('queue')} className="mt-4 text-blue-600 text-sm hover:underline">
          Go to Patient Queue
        </button>
      </div>
    );
  }

  const rec = patient.aiRecommendation;

  if (!rec) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <p className="text-sm text-slate-400">No AI recommendation available for this patient.</p>
        <button onClick={() => setCurrentView('queue')} className="mt-4 text-blue-600 text-sm hover:underline">
          Back to Queue
        </button>
      </div>
    );
  }

  const alreadyDecided = !!patient.nurseDecision;

  const handleAccept = async () => {
    if (!user) return;
    try {
      await acceptRecommendation(patient.id, user.id, user.name);
      setAccepted(true);
    } catch {
      window.alert('Could not save the decision. The patient has not been added to the queue.');
    }
  };

  const handleReassess = () => {
    if (!user) return;
    triggerReassessment(patient.id);
    setCurrentView('new-assessment');
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-5">

      {/* Patient header */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-lg font-bold text-slate-900">{patient.name || 'Unknown Patient'}</span>
            <span className="text-sm text-slate-500 font-mono">{patient.displayId}</span>
            {patient.ageGroup === 'PEDIATRIC' && (
              <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md flex items-center gap-1">
                <Baby size={11} />PEDIATRIC
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-0.5">
            {patient.age}y · {patient.sex} · {patient.chiefComplaint}
          </p>
        </div>
        <button
          onClick={() => setCurrentView('patient-detail')}
          className="text-xs text-blue-600 hover:underline flex items-center gap-1 shrink-0"
        >
          View full detail <ArrowRight size={11} />
        </button>
      </div>

      {/* Safety Gate */}
      {rec.safetyStatus !== 'NORMAL' && (
        <div className={clsx(
          'rounded-xl border p-4',
          rec.safetyStatus === 'URGENT_REVIEW' ? 'bg-red-50 border-red-300' : 'bg-amber-50 border-amber-300'
        )}>
          <div className="flex items-start gap-3">
            <ShieldAlert size={18} className={clsx(
              'mt-0.5 shrink-0',
              rec.safetyStatus === 'URGENT_REVIEW' ? 'text-red-600' : 'text-amber-600'
            )} />
            <div>
              <div className={clsx(
                'text-sm font-bold',
                rec.safetyStatus === 'URGENT_REVIEW' ? 'text-red-800' : 'text-amber-800'
              )}>
                Safety Gate: {rec.safetyStatus === 'URGENT_REVIEW'
                  ? 'Urgent Clinical Review Required'
                  : 'Clinical Verification Recommended'}
              </div>
              {rec.safetyFlag && (
                <p className={clsx(
                  'text-xs mt-1',
                  rec.safetyStatus === 'URGENT_REVIEW' ? 'text-red-700' : 'text-amber-700'
                )}>
                  {rec.safetyFlag}
                </p>
              )}
              {(rec.clinicalRules || []).length > 0 && (
                <div className="mt-2 space-y-0.5">
                  {(rec.clinicalRules || []).map((rule: string) => (
                    <div key={rule} className="flex items-center gap-1.5 text-xs text-red-700">
                      <span className="w-1 h-1 rounded-full bg-red-600 shrink-0" />
                      {rule}
                    </div>
                  ))}
                </div>
              )}
              {rec.isConservative && (
                <p className={clsx(
                  'text-xs mt-2 font-medium',
                  rec.safetyStatus === 'URGENT_REVIEW' ? 'text-red-700' : 'text-amber-700'
                )}>
                  ↑ Conservative pathway applied due to uncertainty or missing data.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Recommendation Card */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
          <Cpu size={14} className="text-slate-500" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">AI Acuity Assessment</span>
          <span className="ml-auto text-xs text-slate-400">{rec.modelVersion}</span>
        </div>

        <div className="p-4">
          <div className="flex items-center gap-6 mb-5">
            <div>
              <div className="text-xs text-slate-500 mb-1.5 font-medium">Recommended Acuity</div>
              <AcuityBadge acuity={rec.acuity} size="lg" />
              <div className="text-xs text-slate-400 mt-1 font-mono">
                {acuityConfig[rec.acuity]?.esiLabel}
              </div>
            </div>
            <div className="h-10 w-px bg-slate-200" />
            <div className="flex-1">
              <div className="text-xs text-slate-500 mb-1.5 font-medium">AI Confidence</div>
              <ConfidenceBar confidence={rec.confidence} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-slate-50 rounded-lg p-2.5 text-center">
              <div className="text-xs text-slate-500 mb-1">Data Completeness</div>
              <div className={clsx(
                'text-base font-bold',
                rec.dataCompleteness >= 80 ? 'text-green-700'
                  : rec.dataCompleteness >= 60 ? 'text-amber-700'
                  : 'text-red-700'
              )}>
                {rec.dataCompleteness}%
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg p-2.5 text-center">
              <div className="text-xs text-slate-500 mb-1">Safety Status</div>
              <SafetyBadge status={rec.safetyStatus} size="sm" />
            </div>
            <div className="bg-slate-50 rounded-lg p-2.5 text-center">
              <div className="text-xs text-slate-500 mb-1">Model</div>
              <div className="text-xs font-semibold text-slate-700">{rec.modelVersion}</div>
            </div>
          </div>

          {/* Key reasons */}
          <div className="mb-3">
            <div className="text-xs font-semibold text-slate-700 mb-2">Key Contributing Factors</div>
            <div className="space-y-1.5">
              {(rec.keyReasons || []).map((r: string, i: number) => (
                <div key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  {r}
                </div>
              ))}
            </div>
          </div>

          {/* Explanation toggle */}
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="flex items-center gap-2 text-xs text-blue-600 hover:text-blue-800 font-medium mt-3"
          >
            <Info size={13} />
            Why this recommendation?
            {showExplanation ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {showExplanation && (
            <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="text-xs font-semibold text-blue-900 mb-2">Why {rec.acuity}?</div>
              <div className="space-y-2 mb-3">
                {(rec.topFactors || []).map((f: any, i: number) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className={clsx(
                      'text-xs font-bold px-1.5 py-0.5 rounded',
                      f.impact === 'HIGH' ? 'bg-red-100 text-red-700'
                        : f.impact === 'MEDIUM' ? 'bg-amber-100 text-amber-700'
                        : 'bg-slate-100 text-slate-600'
                    )}>
                      {f.impact}
                    </span>
                    <span className="text-xs font-medium text-blue-800">{f.feature}:</span>
                    <span className="text-xs text-blue-700">{f.value}</span>
                  </div>
                ))}
              </div>
              {(rec.clinicalRules || []).length > 0 && (
                <div className="mt-2 pt-2 border-t border-blue-200">
                  <div className="text-xs font-semibold text-blue-900 mb-1">Clinical Safety Rules Applied:</div>
                  {(rec.clinicalRules || []).map((rule: string) => (
                    <div key={rule} className="text-xs text-blue-700 flex items-center gap-1.5">
                      <ShieldAlert size={11} />
                      {rule}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-blue-600 mt-2 italic">
                This is an AI recommendation. Clinical judgment by the nurse takes precedence.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Nurse Decision */}
      {!alreadyDecided ? (
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-sm font-semibold text-slate-800 mb-1">Your Decision</div>
          <p className="text-xs text-slate-500 mb-4">The AI recommends. You decide.</p>

          {accepted ? (
            <div className="flex items-center gap-3 text-green-700">
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <Check size={16} className="text-green-600" />
              </div>
              <span className="font-semibold text-sm">Recommendation accepted. Updating queue...</span>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={handleAccept}
                className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold py-3.5 rounded-xl transition-colors"
              >
                <Check size={18} /> ACCEPT
              </button>
              <button
                onClick={() => setShowOverride(true)}
                className="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-bold py-3.5 rounded-xl transition-colors"
              >
                <X size={18} /> OVERRIDE
              </button>
              <button
                onClick={handleReassess}
                className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 rounded-xl transition-colors"
              >
                <RefreshCw size={16} /> REASSESS NOW
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-sm font-semibold text-slate-800 mb-2">Decision Recorded</div>
          <div className="flex items-center gap-3">
            <AcuityBadge acuity={patient.nurseDecision!.finalAcuity} />
            <span className="text-sm text-slate-600">
              {patient.nurseDecision!.action} by {patient.nurseDecision!.nurseName}
            </span>
            {patient.nurseDecision!.action === 'OVERRIDE' && (
              <span className="text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">Override</span>
            )}
          </div>
          {patient.nurseDecision!.overrideNote && (
            <p className="text-xs text-slate-500 mt-2 italic">"{patient.nurseDecision!.overrideNote}"</p>
          )}
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => setCurrentView('queue')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              Back to Queue
            </button>
            <button
              onClick={handleReassess}
              className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <RefreshCw size={14} /> Reassess
            </button>
          </div>
        </div>
      )}

      {showOverride && (
        <OverrideModal
          patient={patient}
          aiAcuity={rec.acuity}
          onClose={() => setShowOverride(false)}
          onOverride={() => { setShowOverride(false); setCurrentView('queue'); }}
        />
      )}
    </div>
  );
}
