import { useState, useMemo, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { SafetyBadge } from '../components/shared/SafetyBadge';
import { formatWaitingTime, formatCountdown } from '../utils/acuity';
import { Search, Clock, AlertTriangle, ChevronRight, Baby, Users, BedDouble, X, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import { Patient } from '../types';

// Red = CRITICAL + HIGH (ESI 1-2), Yellow = MODERATE (ESI 3), Green = LOW (ESI 4-5)
function getColumn(p: Patient): 'red' | 'yellow' | 'green' {
  if (p.currentAcuity === 'CRITICAL' || p.currentAcuity === 'HIGH') return 'red';
  if (p.currentAcuity === 'MODERATE') return 'yellow';
  return 'green';
}

function PatientCard({ patient, onSelect, onDischarge }: { 
  patient: Patient; 
  onSelect: (p: Patient) => void;
  onDischarge: (p: Patient) => void;
}) {
  const countdown = patient.reassessmentDue ? formatCountdown(patient.reassessmentDue) : null;

  return (
    <div className="w-full text-left bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md hover:border-slate-300 transition-all space-y-3">
      {/* Top row: acuity badge + name + discharge button */}
      <div className="flex items-start justify-between gap-2">
        <button onClick={() => onSelect(patient)} className="flex-1 min-w-0 text-left">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-bold text-slate-900 truncate">
              {patient.name || <span className="italic text-slate-400">Unknown</span>}
            </span>
            {patient.ageGroup === 'PEDIATRIC' && (
              <span className="text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded shrink-0">
                <Baby size={11} className="inline mr-0.5" />Pediatric
              </span>
            )}
          </div>
          <div className="text-sm text-slate-500 mt-0.5">
            {patient.age}y · {patient.sex} · <span className="font-mono text-slate-400">{patient.displayId}</span>
          </div>
        </button>
        {/* Bed Assigned button */}
        <button
          onClick={(e) => { e.stopPropagation(); onDischarge(patient); }}
          className="shrink-0 flex items-center gap-1 px-2.5 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-lg transition-colors"
          title="Patient got bed — remove from queue"
        >
          ✓ Bed Assigned
        </button>
      </div>

      {/* Acuity badge */}
      <AcuityBadge acuity={patient.currentAcuity} size="md" />

      {/* Complaint */}
      <p className="text-sm text-slate-600 leading-snug line-clamp-2">{patient.chiefComplaint}</p>

      {/* Vitals row — SpO2, HR, BP, Temp, RR */}
      <div className="flex flex-wrap items-center gap-3 text-center">
        {patient.vitals?.spo2 != null ? (
          <div>
            <div className={clsx('text-sm font-bold tabular-nums',
              patient.vitals.spo2 < 92 ? 'text-red-600' : patient.vitals.spo2 < 95 ? 'text-amber-600' : 'text-slate-700'
            )}>{patient.vitals.spo2}%</div>
            <div className="text-xs text-slate-400">SpO₂</div>
          </div>
        ) : null}
        {patient.vitals?.heartRate != null ? (
          <div>
            <div className={clsx('text-sm font-bold tabular-nums',
              patient.vitals.heartRate > 110 || patient.vitals.heartRate < 50 ? 'text-red-600' : 'text-slate-700'
            )}>{patient.vitals.heartRate}</div>
            <div className="text-xs text-slate-400">HR</div>
          </div>
        ) : null}
        {patient.vitals?.respiratoryRate != null ? (
          <div>
            <div className={clsx('text-sm font-bold tabular-nums',
              patient.vitals.respiratoryRate > 25 ? 'text-red-600' : 'text-slate-700'
            )}>{patient.vitals.respiratoryRate}</div>
            <div className="text-xs text-slate-400">RR</div>
          </div>
        ) : null}
        {patient.vitals?.bpSystolic != null ? (
          <div>
            <div className={clsx('text-sm font-bold tabular-nums',
              patient.vitals.bpSystolic < 90 || patient.vitals.bpSystolic > 160 ? 'text-amber-600' : 'text-slate-700'
            )}>
              {patient.vitals.bpSystolic}/{patient.vitals.bpDiastolic ?? '—'}
            </div>
            <div className="text-xs text-slate-400">BP</div>
          </div>
        ) : null}
        {patient.vitals?.temperature != null ? (
          <div>
            <div className={clsx('text-sm font-bold tabular-nums',
              patient.vitals.temperature > 39 ? 'text-red-600' : patient.vitals.temperature > 37.5 ? 'text-amber-600' : 'text-slate-700'
            )}>{patient.vitals.temperature}°C</div>
            <div className="text-xs text-slate-400">Temp</div>
          </div>
        ) : null}
      </div>

      {/* Symptoms */}
      {patient.symptoms && patient.symptoms.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {patient.symptoms.slice(0, 4).map((s: string) => (
            <span key={s} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{s}</span>
          ))}
          {patient.symptoms.length > 4 && (
            <span className="text-xs text-slate-400">+{patient.symptoms.length - 4} more</span>
          )}
        </div>
      )}

      {/* Bottom row: safety + waiting */}
      <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-100">
        <SafetyBadge status={patient.safetyStatus} size="sm" />
        <div className="text-right">
          <div className="text-sm font-semibold text-slate-700 flex items-center justify-end gap-1">
            <Clock size={13} className="text-slate-400" />
            {formatWaitingTime(patient.waitingTime)}
          </div>
          {countdown && (
            <div className={clsx('text-xs font-mono font-bold mt-0.5',
              countdown.overdue ? 'text-red-600' : countdown.urgent ? 'text-amber-600' : 'text-slate-400'
            )}>
              {countdown.overdue ? 'OVERDUE' : `↺ ${countdown.label}`}
            </div>
          )}
        </div>
      </div>

      {patient.nurseDecision?.action === 'OVERRIDE' && (
        <div className="text-xs text-amber-700 font-semibold">
          ⚠ Nurse override from {patient.aiRecommendation?.acuity}
        </div>
      )}
    </div>
  );
}

export function PatientQueueScreen() {
  const { patients, surgePatients, surgeActive, setSelectedPatient, setCurrentView, fetchQueue, dischargePatient } = useAppStore();
  const allPatients = surgeActive ? [...patients, ...surgePatients] : patients;

  // Refresh queue from backend on mount
  useEffect(() => { fetchQueue(); }, []);
  const [search, setSearch] = useState('');
  const [safetyFilter, setSafetyFilter] = useState(false);
  const [bedPatient, setBedPatient] = useState<Patient | null>(null);
  const [assigningBed, setAssigningBed] = useState(false);
  const [bedError, setBedError] = useState('');

  const filtered = useMemo(() => {
    let list = allPatients.filter(p => p.status === 'WAITING' || p.status === 'IN_PROGRESS');
    if (safetyFilter) list = list.filter(p => p.safetyStatus !== 'NORMAL');
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p =>
        p.displayId.toLowerCase().includes(q) ||
        p.name?.toLowerCase().includes(q) ||
        p.chiefComplaint.toLowerCase().includes(q)
      );
    }
    return list;
  }, [allPatients, search, safetyFilter]);

  const red    = filtered.filter(p => getColumn(p) === 'red');
  const yellow = filtered.filter(p => getColumn(p) === 'yellow');
  const green  = filtered.filter(p => getColumn(p) === 'green');

  const openPatient = (p: Patient) => {
    setSelectedPatient(p.id);
    setCurrentView('patient-detail');
  };

  const handleBedAssign = async () => {
    if (!bedPatient) return;
    setAssigningBed(true);
    setBedError('');
    try {
      await dischargePatient(bedPatient.id);
      setBedPatient(null);
    } catch {
      setBedError('Could not update the patient status. Please try again.');
    } finally {
      setAssigningBed(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-5 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Patient Queue</h1>
            <p className="text-base text-slate-500 mt-1">{filtered.length} patients</p>
          </div>
          <button
            onClick={() => setCurrentView('new-assessment')}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-base font-semibold px-5 py-2.5 rounded-xl transition-colors"
          >
            + New Patient
          </button>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-52">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name, ID, or complaint..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={() => setSafetyFilter(!safetyFilter)}
            className={clsx(
              'flex items-center gap-2 text-base font-semibold px-4 py-2.5 rounded-xl border transition-colors',
              safetyFilter
                ? 'bg-amber-50 border-amber-300 text-amber-700'
                : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
            )}
          >
            <AlertTriangle size={16} />
            Safety Flags
          </button>
        </div>
      </div>

      {/* Three columns */}
      <div className="flex-1 overflow-hidden grid grid-cols-3 divide-x divide-slate-200">

        {/* RED — Critical */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3.5 bg-red-50 border-b border-red-200 shrink-0">
            <span className="w-3.5 h-3.5 rounded-full bg-red-500 shrink-0" />
            <span className="text-base font-bold text-red-700 uppercase tracking-wide">ESI 1-2 — Critical / High</span>
            <span className="ml-auto text-base font-bold text-red-600 bg-red-100 px-2.5 py-0.5 rounded-full">
              {red.length}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-red-50/30">
            {red.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
                <Users size={28} className="mb-2 text-slate-300" />
                <p className="text-sm font-medium">No critical patients</p>
              </div>
            ) : (
              red.map(p => <PatientCard key={p.id} patient={p} onSelect={openPatient} onDischarge={setBedPatient} />)
            )}
          </div>
        </div>

        {/* YELLOW — High / Moderate */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3.5 bg-yellow-50 border-b border-yellow-200 shrink-0">
            <span className="w-3.5 h-3.5 rounded-full bg-yellow-400 shrink-0" />
            <span className="text-base font-bold text-yellow-700 uppercase tracking-wide">ESI 3 — Moderate / Urgent</span>
            <span className="ml-auto text-base font-bold text-yellow-600 bg-yellow-100 px-2.5 py-0.5 rounded-full">
              {yellow.length}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-yellow-50/30">
            {yellow.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
                <Users size={28} className="mb-2 text-slate-300" />
                <p className="text-sm font-medium">No high/moderate patients</p>
              </div>
            ) : (
              yellow.map(p => <PatientCard key={p.id} patient={p} onSelect={openPatient} onDischarge={setBedPatient} />)
            )}
          </div>
        </div>

        {/* GREEN — Low */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-3 px-5 py-3.5 bg-green-50 border-b border-green-200 shrink-0">
            <span className="w-3.5 h-3.5 rounded-full bg-green-500 shrink-0" />
            <span className="text-base font-bold text-green-700 uppercase tracking-wide">ESI 4-5 — Low / Non-Urgent</span>
            <span className="ml-auto text-base font-bold text-green-600 bg-green-100 px-2.5 py-0.5 rounded-full">
              {green.length}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-green-50/30">
            {green.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
                <Users size={28} className="mb-2 text-slate-300" />
                <p className="text-sm font-medium">No low-acuity patients</p>
              </div>
            ) : (
              green.map(p => <PatientCard key={p.id} patient={p} onSelect={openPatient} onDischarge={setBedPatient} />)
            )}
          </div>
        </div>

      </div>

      {bedPatient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 backdrop-blur-sm p-4">
          <div className="w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100 text-green-700"><BedDouble size={20} /></div>
                <div><h2 className="text-base font-bold text-slate-900">Confirm bed assignment</h2><p className="text-xs text-slate-500">This removes the patient from the active queue.</p></div>
              </div>
              <button onClick={() => !assigningBed && setBedPatient(null)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"><X size={18} /></button>
            </div>
            <div className="p-5">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="font-semibold text-slate-900">{bedPatient.name || 'Unknown patient'}</p>
                <p className="mt-1 text-xs text-slate-500">{bedPatient.displayId} · {bedPatient.age}y · {bedPatient.chiefComplaint}</p>
              </div>
              {bedError && <p className="mt-3 text-xs font-medium text-red-600">{bedError}</p>}
            </div>
            <div className="flex gap-3 bg-slate-50 px-5 py-4">
              <button disabled={assigningBed} onClick={() => setBedPatient(null)} className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100">Cancel</button>
              <button disabled={assigningBed} onClick={handleBedAssign} className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-green-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-green-700 disabled:bg-slate-300"><CheckCircle2 size={16} />{assigningBed ? 'Assigning…' : 'Confirm bed'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
