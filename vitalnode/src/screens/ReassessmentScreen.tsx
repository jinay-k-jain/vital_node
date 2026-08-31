import { useMemo, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { SafetyBadge } from '../components/shared/SafetyBadge';
import { formatCountdown, formatWaitingTime } from '../utils/acuity';
import { Clock, RefreshCw, AlertTriangle, ChevronRight, Users } from 'lucide-react';
import clsx from 'clsx';
import { Patient } from '../types';

// Red   = CRITICAL or HIGH (ESI 1–2)
// Yellow = MODERATE (ESI 3)
// Green  = LOW acuity
function getColumn(p: Patient): 'red' | 'yellow' | 'green' {
  if (p.currentAcuity === 'CRITICAL' || p.currentAcuity === 'HIGH') return 'red';
  if (p.currentAcuity === 'MODERATE') return 'yellow';
  return 'green';
}

function PatientCard({
  patient,
  onView,
  onReassess,
}: {
  patient: Patient;
  onView: (p: Patient) => void;
  onReassess: (p: Patient) => void;
}) {
  const countdown = patient.reassessmentDue ? formatCountdown(patient.reassessmentDue) : null;
  const isOverdue = countdown?.overdue ?? false;
  const isUrgent  = countdown?.urgent  ?? false;

  return (
    <div className={clsx(
      'bg-white border rounded-2xl p-4 space-y-3 shadow-sm transition-shadow hover:shadow-md',
      isOverdue ? 'border-red-300' : isUrgent ? 'border-amber-300' : 'border-slate-200',
    )}>
      {/* Name + ID */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-base font-bold text-slate-900 truncate">
            {patient.name || <span className="italic text-slate-400">Unknown Patient</span>}
          </p>
          <p className="text-sm text-slate-400 font-mono mt-0.5">{patient.displayId}</p>
        </div>
        {isOverdue && (
          <span className="shrink-0 text-xs font-bold text-red-600 bg-red-100 border border-red-200 px-2 py-1 rounded-lg">
            OVERDUE
          </span>
        )}
        {!isOverdue && isUrgent && (
          <span className="shrink-0 text-xs font-bold text-amber-700 bg-amber-100 border border-amber-200 px-2 py-1 rounded-lg">
            DUE SOON
          </span>
        )}
      </div>

      {/* Acuity badge */}
      <AcuityBadge acuity={patient.currentAcuity} size="md" />

      {/* Chief complaint */}
      <p className="text-sm text-slate-600 leading-snug line-clamp-2">{patient.chiefComplaint}</p>

      {/* Countdown + waiting */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5 text-slate-500">
          <Clock size={14} />
          <span className="font-medium">{formatWaitingTime(patient.waitingTime)} waiting</span>
        </div>
        {countdown && (
          <span className={clsx(
            'font-mono font-bold text-sm',
            isOverdue ? 'text-red-600' : isUrgent ? 'text-amber-600' : 'text-slate-400',
          )}>
            {isOverdue ? '⚠ Overdue' : `↺ ${countdown.label}`}
          </span>
        )}
      </div>

      {/* Safety badge */}
      <div className="flex items-center justify-between">
        <SafetyBadge status={patient.safetyStatus} size="sm" />
        <span className="text-xs text-slate-400">×{patient.reassessmentCount} reassessed</span>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onView(patient)}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-semibold border border-slate-200 rounded-xl text-slate-700 hover:bg-slate-50 transition-colors"
        >
          <ChevronRight size={15} />
          View Record
        </button>
        <button
          onClick={() => onReassess(patient)}
          className="flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors"
        >
          <RefreshCw size={15} />
          Reassess Now
        </button>
      </div>
    </div>
  );
}

export function ReassessmentScreen() {
  const {
    patients, surgePatients, surgeActive,
    setSelectedPatient, setCurrentView,
    triggerReassessment, user, fetchQueue,
  } = useAppStore();

  // Load live patients from backend on mount
  useEffect(() => { fetchQueue(); }, []);

  const allPatients = surgeActive ? [...patients, ...surgePatients] : patients;
  const waiting = allPatients.filter(p => p.status === 'WAITING' || p.status === 'IN_PROGRESS');

  // Only patients with a reassessment due date
  const due = useMemo(() => {
    return waiting.filter(p => p.reassessmentDue);
  }, [waiting]);

  const red    = due.filter(p => getColumn(p) === 'red');
  const yellow = due.filter(p => getColumn(p) === 'yellow');
  const green  = due.filter(p => getColumn(p) === 'green');

  const onView = (p: Patient) => {
    setSelectedPatient(p.id);
    setCurrentView('patient-detail');
  };

  const onReassess = (p: Patient) => {
    if (user) {
      triggerReassessment(p.id);
      setSelectedPatient(p.id);
      setCurrentView('new-assessment');
    }
  };

  // Summary counts
  const overdueCount = due.filter(p => {
    const cd = p.reassessmentDue ? formatCountdown(p.reassessmentDue) : null;
    return cd?.overdue;
  }).length;

  return (
    <div className="flex flex-col h-full">

      {/* Header */}
      <div className="px-6 py-5 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Reassessment Queue</h1>
            <p className="text-base text-slate-500 mt-1">
              {due.length} patient{due.length !== 1 ? 's' : ''} scheduled for reassessment
              {overdueCount > 0 && (
                <span className="ml-2 text-red-600 font-semibold">
                  · {overdueCount} overdue
                </span>
              )}
            </p>
          </div>
          {overdueCount > 0 && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-xl">
              <AlertTriangle size={18} className="shrink-0" />
              <span className="text-sm font-bold">{overdueCount} overdue</span>
            </div>
          )}
        </div>
      </div>

      {/* Empty state */}
      {due.length === 0 && (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-400">
          <RefreshCw size={40} className="text-slate-300" />
          <p className="text-lg font-semibold text-slate-500">No patients require reassessment right now.</p>
          <p className="text-sm">Check back once assessments have been submitted.</p>
        </div>
      )}

      {/* Three columns */}
      {due.length > 0 && (
        <div className="flex-1 overflow-hidden grid grid-cols-3 divide-x divide-slate-200">

          {/* RED — Critical */}
          <div className="flex flex-col overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-3.5 bg-red-50 border-b border-red-200 shrink-0">
              <span className="w-3.5 h-3.5 rounded-full bg-red-500 shrink-0" />
              <div>
                <span className="text-base font-bold text-red-700 uppercase tracking-wide">ESI 1-2 — Critical / High</span>
                <p className="text-xs text-red-500 mt-0.5">Immediate — Emergent</p>
              </div>
              <span className="ml-auto text-base font-bold text-red-600 bg-red-100 px-2.5 py-0.5 rounded-full shrink-0">
                {red.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-red-50/20">
              {red.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 text-center">
                  <Users size={28} className="mb-2 text-slate-300" />
                  <p className="text-sm font-medium">No critical patients</p>
                </div>
              ) : (
                red.map(p => (
                  <PatientCard key={p.id} patient={p} onView={onView} onReassess={onReassess} />
                ))
              )}
            </div>
          </div>

          {/* YELLOW — High / Moderate */}
          <div className="flex flex-col overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-3.5 bg-yellow-50 border-b border-yellow-200 shrink-0">
              <span className="w-3.5 h-3.5 rounded-full bg-yellow-400 shrink-0" />
              <div>
                <span className="text-base font-bold text-yellow-700 uppercase tracking-wide">ESI 3 — Moderate / Urgent</span>
                <p className="text-xs text-yellow-600 mt-0.5">Reassess within scheduled window</p>
              </div>
              <span className="ml-auto text-base font-bold text-yellow-600 bg-yellow-100 px-2.5 py-0.5 rounded-full shrink-0">
                {yellow.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-yellow-50/20">
              {yellow.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 text-center">
                  <Users size={28} className="mb-2 text-slate-300" />
                  <p className="text-sm font-medium">No high/moderate patients</p>
                </div>
              ) : (
                yellow.map(p => (
                  <PatientCard key={p.id} patient={p} onView={onView} onReassess={onReassess} />
                ))
              )}
            </div>
          </div>

          {/* GREEN — Low */}
          <div className="flex flex-col overflow-hidden">
            <div className="flex items-center gap-3 px-5 py-3.5 bg-green-50 border-b border-green-200 shrink-0">
              <span className="w-3.5 h-3.5 rounded-full bg-green-500 shrink-0" />
              <div>
                <span className="text-base font-bold text-green-700 uppercase tracking-wide">ESI 4-5 — Low / Non-Urgent</span>
                <p className="text-xs text-green-600 mt-0.5">Routine reassessment scheduled</p>
              </div>
              <span className="ml-auto text-base font-bold text-green-600 bg-green-100 px-2.5 py-0.5 rounded-full shrink-0">
                {green.length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-green-50/20">
              {green.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 text-center">
                  <Users size={28} className="mb-2 text-slate-300" />
                  <p className="text-sm font-medium">No low-acuity patients</p>
                </div>
              ) : (
                green.map(p => (
                  <PatientCard key={p.id} patient={p} onView={onView} onReassess={onReassess} />
                ))
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
