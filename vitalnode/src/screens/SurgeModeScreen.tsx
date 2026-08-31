import React from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { Zap, ZapOff, Users, AlertTriangle, Clock, ShieldAlert, Activity } from 'lucide-react';
import clsx from 'clsx';
import { formatWaitingTime, acuityPriority } from '../utils/acuity';

export function SurgeModeScreen() {
  const { patients, surgePatients, surgeActive, activateSurge, deactivateSurge, setCurrentView, setSelectedPatient } = useAppStore();  const allPatients = surgeActive ? [...patients, ...surgePatients] : patients;
  const waiting = allPatients.filter(p => p.status === 'WAITING' || p.status === 'IN_PROGRESS');
  const now = new Date();

  const stats = {
    total: waiting.length,
    critical: waiting.filter(p => p.currentAcuity === 'CRITICAL').length,
    high: waiting.filter(p => p.currentAcuity === 'HIGH').length,
    overdue: waiting.filter(p => p.reassessmentDue && p.reassessmentDue < now).length,
    safetyFlag: waiting.filter(p => p.safetyStatus !== 'NORMAL').length,
  };

  const priorityQueue = [...waiting]
    .sort((a, b) => {
      const ap = acuityPriority(a.currentAcuity);
      const bp = acuityPriority(b.currentAcuity);
      if (ap !== bp) return ap - bp;
      return b.waitingTime - a.waitingTime;
    })
    .slice(0, 15);

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-6xl mx-auto w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Surge Mode</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Simulates high-volume emergency department operation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {surgeActive ? (
            <button
              onClick={deactivateSurge}
              className="flex items-center gap-2 bg-slate-700 hover:bg-slate-800 text-white font-bold px-4 py-2.5 rounded-xl transition-colors"
            >
              <ZapOff size={16} />
              Deactivate Surge
            </button>
          ) : (
            <button
              onClick={activateSurge}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white font-bold px-4 py-2.5 rounded-xl transition-colors"
            >
              <Zap size={16} />
              SIMULATE 3× SURGE
            </button>
          )}
        </div>
      </div>

      {/* Surge indicator */}
      {surgeActive && (
        <div className="bg-red-50 border border-red-300 rounded-xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
            <Zap size={18} className="text-red-600" />
          </div>
          <div>
            <div className="text-sm font-bold text-red-800">SURGE MODE ACTIVE — 3× Volume Simulation</div>
            <p className="text-xs text-red-700 mt-0.5">
              Clinical safety standards are maintained. Priority visibility and reassessment deadlines remain active.
            </p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: 'Total Patients', value: stats.total, color: 'text-slate-800', icon: Users },
          { label: 'Critical', value: stats.critical, color: 'text-red-700', icon: AlertTriangle },
          { label: 'High', value: stats.high, color: 'text-orange-700', icon: Activity },
          { label: 'Reassess Overdue', value: stats.overdue, color: stats.overdue > 0 ? 'text-red-600' : 'text-slate-400', icon: Clock },
          { label: 'Safety Flags', value: stats.safetyFlag, color: stats.safetyFlag > 0 ? 'text-amber-600' : 'text-slate-400', icon: ShieldAlert },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="bg-white border border-slate-200 rounded-xl p-3 text-center">
            <Icon size={16} className={clsx('mx-auto mb-1.5', color)} />
            <div className={clsx('text-2xl font-bold', color)}>{value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Queue table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <span className="text-sm font-semibold text-slate-800">Priority Queue ({priorityQueue.length}{surgeActive ? ` of ${waiting.length}` : ''})</span>
          <button onClick={() => setCurrentView('queue')} className="text-xs text-blue-600 hover:underline">
            Full queue →
          </button>
        </div>
        <div className="divide-y divide-slate-100">
          {priorityQueue.map((p, i) => {
            const isOverdue = p.reassessmentDue && p.reassessmentDue < now;
            return (
              <button
                key={p.id}
                onClick={() => { setSelectedPatient(p.id); setCurrentView('patient-detail'); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors text-left"
              >
                <span className="text-xs font-bold text-slate-400 w-5 shrink-0">{i + 1}</span>
                <AcuityBadge acuity={p.currentAcuity} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-800 truncate">{p.name || p.displayId}</div>
                  <div className="text-xs text-slate-500 truncate">{p.chiefComplaint}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-xs text-slate-600">{formatWaitingTime(p.waitingTime)}</div>
                  {isOverdue && <div className="text-xs text-red-600 font-bold">REASSESS OVERDUE</div>}
                  {p.safetyStatus !== 'NORMAL' && !isOverdue && (
                    <div className="text-xs text-amber-700 font-medium">⚠ Verify</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600 leading-relaxed">
        <p className="font-semibold text-slate-700 mb-1">Important — Surge Mode behaviour:</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>Clinical safety thresholds are never lowered during surge conditions.</li>
          <li>Reassessment timers continue independently of department volume.</li>
          <li>Critical and high-acuity patients always remain visible at the top of the queue.</li>
          <li>Safety verification requirements remain active for all flagged patients.</li>
          <li>All nurse decisions during surge mode are fully audited.</li>
        </ul>
      </div>
    </div>
  );
}
