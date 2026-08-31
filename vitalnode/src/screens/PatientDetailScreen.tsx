import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { SafetyBadge } from '../components/shared/SafetyBadge';
import { ConfidenceBar } from '../components/shared/ConfidenceBar';
import { VitalDisplay } from '../components/shared/VitalDisplay';
import { OverrideModal } from '../components/OverrideModal';
import { patientApi } from '../lib/api';
import { formatWaitingTime, formatCountdown, ageGroupLabel } from '../utils/acuity';
import {
  Clock, RefreshCw, ArrowLeft, Baby, User, ShieldAlert, Activity,
  Heart, Wind, Thermometer, Eye, ChevronRight, AlertTriangle, Edit3
} from 'lucide-react';
import clsx from 'clsx';
import { format } from 'date-fns';
import { TimelineEvent } from '../types';

function TimelineItem({ event }: { event: TimelineEvent }) {
  const typeConfig: Record<string, { color: string; bg: string }> = {
    ARRIVAL: { color: 'text-blue-600', bg: 'bg-blue-100' },
    AI_ASSESSMENT: { color: 'text-violet-600', bg: 'bg-violet-100' },
    ACCEPTED: { color: 'text-green-600', bg: 'bg-green-100' },
    OVERRIDE: { color: 'text-amber-600', bg: 'bg-amber-100' },
    VITAL_RECEIVED: { color: 'text-slate-600', bg: 'bg-slate-100' },
    ASSESSMENT_CREATED: { color: 'text-blue-600', bg: 'bg-blue-100' },
    REASSESS_REQUESTED: { color: 'text-orange-600', bg: 'bg-orange-100' },
  };
  const cfg = typeConfig[event.type] || typeConfig.ASSESSMENT_CREATED;

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center shrink-0', cfg.bg)}>
          <span className={clsx('w-2 h-2 rounded-full', cfg.color.replace('text-', 'bg-'))} />
        </div>
        <div className="w-px flex-1 bg-slate-200 my-1" />
      </div>
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">
            {format(event.timestamp, 'HH:mm')}
          </span>
          {event.acuity && <AcuityBadge acuity={event.acuity} size="sm" />}
        </div>
        <div className="text-sm font-semibold text-slate-800 mt-0.5">{event.title}</div>
        <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{event.description}</div>
        {event.confidence !== undefined && (
          <div className="mt-1 w-40">
            <ConfidenceBar confidence={event.confidence} size="sm" />
          </div>
        )}
      </div>
    </div>
  );
}

export function PatientDetailScreen() {
  const { patients, selectedPatientId, setCurrentView, triggerReassessment, user } = useAppStore();
  const livePatient = patients.find(p => p.id === selectedPatientId);

  // Stable ref — never goes blank when WebSocket updates the list
  const stablePatient = useRef<typeof livePatient>(undefined);
  if (livePatient) stablePatient.current = livePatient;
  const patient = stablePatient.current;

  const [showOverride, setShowOverride] = useState(false);
  const [countdown, setCountdown] = useState(patient?.reassessmentDue ? formatCountdown(patient.reassessmentDue) : null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  // Load timeline from backend
  useEffect(() => {
    if (!patient) return;
    patientApi.getTimeline(patient.displayId)
      .then((events: any[]) => {
        setTimeline(events.map((e: any) => ({
          id: e.id,
          timestamp: new Date(e.timestamp),
          type: e.type,
          title: e.title,
          description: e.description,
          acuity: e.acuity,
          confidence: e.confidence,
        })));
      })
      .catch(() => setTimeline([]));
  }, [patient?.id]);

  useEffect(() => {
    if (!patient?.reassessmentDue) return;
    const interval = setInterval(() => {
      setCountdown(formatCountdown(patient.reassessmentDue!));
    }, 1000);
    return () => clearInterval(interval);
  }, [patient?.reassessmentDue]);

  if (!patient) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <p className="text-sm text-slate-400">Select a patient from the queue to view details.</p>
        <button onClick={() => setCurrentView('queue')} className="mt-4 text-blue-600 text-sm hover:underline">
          Go to Patient Queue
        </button>
      </div>
    );
  }

  // Safe vitals with defaults so nothing crashes on missing data
  const vitals = patient.vitals || { timestamp: new Date(), source: 'Manual Entry' };

  const handleReassess = () => {
    if (!user) return;
    triggerReassessment(patient.id);
    setCurrentView('new-assessment');
  };

  return (
    <div className="flex flex-col lg:flex-row h-full overflow-hidden">
      {/* Left: Details */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <button
            onClick={() => setCurrentView('queue')}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 shrink-0 mt-0.5"
          >
            <ArrowLeft size={14} className="text-slate-600" />
          </button>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900">{patient.name || 'Unknown Patient'}</h1>
              <span className="text-sm text-slate-400 font-mono">{patient.displayId}</span>
              {patient.ageGroup === 'PEDIATRIC' && (
                <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md flex items-center gap-1">
                  <Baby size={10} />PEDIATRIC
                </span>
              )}
              {patient.ageGroup === 'OLDER_ADULT' && (
                <span className="text-xs font-medium text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-md">
                  Older Adult
                </span>
              )}
            </div>
            <div className="text-sm text-slate-500 mt-0.5">
              {patient.age}y · {patient.sex} · {patient.arrivalMode} · Waiting {formatWaitingTime(patient.waitingTime)}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <AcuityBadge acuity={patient.currentAcuity} />
            <SafetyBadge status={patient.safetyStatus} />
          </div>
        </div>

        {/* Chief complaint */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Chief Complaint</div>
          <p className="text-sm text-slate-800 leading-relaxed">"{patient.chiefComplaint}"</p>
          {patient.symptoms.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {patient.symptoms.map(s => (
                <span key={s} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded-full border border-slate-200">
                  {s}
                </span>
              ))}
            </div>
          )}
          {patient.dangerSigns.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {patient.dangerSigns.map(d => (
                <span key={d} className="text-xs bg-red-50 text-red-700 border border-red-200 px-2 py-1 rounded-full font-medium">
                  ⚠ {d}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Vitals */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Vitals</div>
            <span className="text-xs text-slate-400">
              {vitals.timestamp ? format(new Date(vitals.timestamp), 'HH:mm:ss') : '—'}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <VitalDisplay
              label="SpO₂"
              value={vitals.spo2}
              unit="%"
              source={vitals.source}
              alert={!!(vitals.spo2 && vitals.spo2 < 90)}
              warning={!!(vitals.spo2 && vitals.spo2 < 95 && vitals.spo2 >= 90)}
              size="sm"
            />
            <VitalDisplay label="Heart Rate" value={vitals.heartRate} unit="bpm" source={vitals.source} alert={!!(vitals.heartRate && (vitals.heartRate > 120 || vitals.heartRate < 50))} size="sm" />
            <VitalDisplay label="Resp. Rate" value={vitals.respiratoryRate} unit="/min" source={vitals.source} alert={!!(vitals.respiratoryRate && vitals.respiratoryRate > 25)} size="sm" />
            <VitalDisplay
              label="Blood Pressure"
              value={vitals.bpSystolic !== undefined && vitals.bpSystolic !== null ? `${vitals.bpSystolic}/${vitals.bpDiastolic}` : undefined}
              unit="mmHg"
              source={vitals.source}
              alert={!!(vitals.bpSystolic && vitals.bpSystolic < 90)}
              size="sm"
            />
            <VitalDisplay label="Temperature" value={vitals.temperature} unit="°C" source={vitals.source} warning={!!(vitals.temperature && vitals.temperature > 37.5)} size="sm" />
            <div className="rounded-lg border bg-white p-2">
              <div className="text-xs text-slate-500 font-medium mb-1">AVPU</div>
              <div className={clsx(
                'text-sm font-bold',
                vitals.avpu === 'Alert' ? 'text-green-700' :
                vitals.avpu === 'Voice' ? 'text-amber-700' :
                vitals.avpu === 'Pain' ? 'text-orange-700' : 'text-red-700'
              )}>
                {vitals.avpu || '—'}
              </div>
            </div>
          </div>

          {!patient.deviceConnected && (
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-slate-300" />
              Vitals Monitor: Disconnected — Manual entry
            </div>
          )}
        </div>

        {/* History */}
        <div className="bg-white border border-slate-200 rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Patient History</div>
          {patient.history.available ? (
            <div className="space-y-2">
              {patient.history.conditions && patient.history.conditions.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-slate-700">Conditions: </span>
                  <span className="text-xs text-slate-600">{patient.history.conditions.join(', ')}</span>
                </div>
              )}
              {patient.history.medications && patient.history.medications.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-slate-700">Medications: </span>
                  <span className="text-xs text-slate-600">{patient.history.medications.join(', ')}</span>
                </div>
              )}
              {patient.history.allergies && patient.history.allergies.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-slate-700">Allergies: </span>
                  <span className="text-xs text-red-700 font-medium">{patient.history.allergies.join(', ')}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-500 italic">
              <span className="w-2 h-2 rounded-full bg-slate-300" />
              No previous hospital record available.
            </div>
          )}
        </div>

        {/* AI Recommendation summary */}
        {patient.aiRecommendation && (
          <div className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">AI Assessment</div>
              <button
                onClick={() => setCurrentView('ai-result')}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                Full details <ChevronRight size={11} />
              </button>
            </div>
            <div className="flex items-center gap-4 mb-3">
              <AcuityBadge acuity={patient.aiRecommendation.acuity} />
              <div className="flex-1">
                <ConfidenceBar confidence={patient.aiRecommendation.confidence} />
              </div>
            </div>
            {patient.aiRecommendation.safetyFlag && (
              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-3">
                <ShieldAlert size={13} className="text-amber-600 mt-0.5 shrink-0" />
                <span className="text-xs text-amber-800">{patient.aiRecommendation.safetyFlag}</span>
              </div>
            )}
            {patient.nurseDecision && (
              <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                <span className="text-xs text-slate-500">Nurse decision:</span>
                <AcuityBadge acuity={patient.nurseDecision.finalAcuity} size="sm" />
                {patient.nurseDecision.action === 'OVERRIDE' && (
                  <span className="text-xs text-amber-700 font-medium bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">Override</span>
                )}
                <span className="text-xs text-slate-400">{patient.nurseDecision.nurseName}</span>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pb-4">
          <button
            onClick={handleReassess}
            className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-colors"
          >
            <RefreshCw size={16} />
            REASSESS NOW
          </button>
          <button
            onClick={() => setShowOverride(true)}
            className="flex-1 flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-bold py-3 rounded-xl transition-colors"
          >
            <Edit3 size={16} />
            OVERRIDE
          </button>
          <button
            onClick={() => setCurrentView('ai-result')}
            className="flex-1 flex items-center justify-center gap-2 bg-slate-700 hover:bg-slate-800 text-white font-bold py-3 rounded-xl transition-colors"
          >
            <Activity size={16} />
            AI RESULT
          </button>
        </div>
      </div>

      {/* Right: Timeline + countdown */}
      <div className="w-full lg:w-72 border-t lg:border-t-0 lg:border-l border-slate-200 bg-slate-50 overflow-y-auto scrollbar-thin p-4 shrink-0">
        {/* Reassessment timer */}
        {patient.reassessmentDue && (
          <div className={clsx(
            'rounded-xl border p-3 mb-4',
            countdown?.overdue ? 'bg-red-50 border-red-300' : countdown?.urgent ? 'bg-amber-50 border-amber-300' : 'bg-white border-slate-200'
          )}>
            <div className="flex items-center gap-2 mb-1">
              <Clock size={13} className={countdown?.overdue ? 'text-red-600' : countdown?.urgent ? 'text-amber-600' : 'text-slate-500'} />
              <span className="text-xs font-semibold text-slate-700">Reassessment</span>
            </div>
            {countdown?.overdue ? (
              <div className="text-sm font-bold text-red-700">OVERDUE</div>
            ) : (
              <div className={clsx('text-2xl font-bold font-mono tabular-nums', countdown?.urgent ? 'text-amber-700' : 'text-slate-800')}>
                {countdown?.label}
              </div>
            )}
            <div className="text-xs text-slate-400 mt-1">×{patient.reassessmentCount} reassessment{patient.reassessmentCount !== 1 ? 's' : ''}</div>
          </div>
        )}

        {/* Timeline */}
        <div>
          <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-3">Patient Timeline</h3>
          {timeline.length === 0 ? (
            <p className="text-xs text-slate-400">No events recorded yet.</p>
          ) : (
            timeline.map(event => (
              <TimelineItem key={event.id} event={event} />
            ))
          )}
        </div>
      </div>

      {showOverride && patient.aiRecommendation && (
        <OverrideModal
          patient={patient}
          aiAcuity={patient.aiRecommendation.acuity}
          onClose={() => setShowOverride(false)}
          onOverride={() => setShowOverride(false)}
        />
      )}
    </div>
  );
}
