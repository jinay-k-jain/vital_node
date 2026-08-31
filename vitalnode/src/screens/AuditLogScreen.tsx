import React, { useState, useMemo } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { Search, FileText, Shield, ChevronDown, ChevronUp } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';
import { NurseActionType } from '../types';

const ACTION_LABELS: Record<NurseActionType, { label: string; color: string }> = {
  ACCEPTED: { label: 'Accepted', color: 'bg-green-100 text-green-800' },
  OVERRIDE: { label: 'Override', color: 'bg-amber-100 text-amber-800' },
  REASSESS_REQUESTED: { label: 'Reassess', color: 'bg-blue-100 text-blue-800' },
  ASSESSMENT_CREATED: { label: 'Created', color: 'bg-slate-100 text-slate-700' },
  VITAL_UPDATED: { label: 'Vitals Updated', color: 'bg-blue-100 text-blue-800' },
  OBSERVATION_ADDED: { label: 'Observation', color: 'bg-slate-100 text-slate-700' },
};

export function AuditLogScreen() {
  const { auditLog, fetchAuditLog } = useAppStore();
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'OVERRIDE' | 'REASSESS_REQUESTED'>('ALL');

  // Load from backend on mount
  React.useEffect(() => { fetchAuditLog(); }, []);

  const filtered = useMemo(() => {
    let list = [...auditLog];
    if (filter !== 'ALL') list = list.filter(e => e.eventType === filter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(e =>
        e.patientDisplayId.toLowerCase().includes(q) ||
        e.nurseName.toLowerCase().includes(q) ||
        e.overrideReason?.toLowerCase().includes(q)
      );
    }
    return list.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [auditLog, search, filter]);

  return (
    <div className="p-4 sm:p-6 space-y-4 max-w-6xl mx-auto w-full">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Audit Log</h1>
        <p className="text-sm text-slate-500 mt-0.5">Complete record of all clinical decisions and AI recommendations. Immutable.</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by patient, nurse, or reason..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-1.5 bg-slate-100 rounded-lg p-1">
          {([['ALL', 'All'], ['OVERRIDE', 'Overrides'], ['REASSESS_REQUESTED', 'Reassess']] as const).map(([val, label]) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={clsx(
                'text-xs font-semibold px-2.5 py-1 rounded-md transition-colors',
                filter === val ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Log */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="grid grid-cols-[100px_100px_90px_90px_120px_80px_1fr] gap-2 px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
          <div>Time</div>
          <div>Patient</div>
          <div>AI Rec.</div>
          <div>Final</div>
          <div>Action</div>
          <div>Confidence</div>
          <div>Details</div>
        </div>

        {filtered.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <FileText size={28} className="text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-400">No audit entries match the current filter.</p>
          </div>
        ) : (
          filtered.map((entry) => {
            const actionCfg = ACTION_LABELS[entry.eventType] || ACTION_LABELS.ASSESSMENT_CREATED;
            const isExpanded = expandedId === entry.id;
            const isOverride = entry.eventType === 'OVERRIDE';

            return (
              <div key={entry.id} className={clsx('border-b border-slate-100', isOverride && 'bg-amber-50/50')}>
                <button
                  onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  className="w-full text-left"
                >
                  <div className="grid grid-cols-[100px_100px_90px_90px_120px_80px_1fr] gap-2 px-4 py-3 items-center hover:bg-slate-50 transition-colors">
                    <div className="text-xs font-mono text-slate-600">
                      {format(entry.timestamp, 'HH:mm:ss')}
                    </div>
                    <div className="text-xs font-mono text-slate-700 font-semibold">{entry.patientDisplayId}</div>
                    <div>
                      {entry.aiRecommendation && <AcuityBadge acuity={entry.aiRecommendation} size="sm" />}
                    </div>
                    <div>
                      {entry.finalAcuity && <AcuityBadge acuity={entry.finalAcuity} size="sm" />}
                    </div>
                    <div>
                      <span className={clsx('text-xs font-semibold px-2 py-0.5 rounded-full', actionCfg.color)}>
                        {actionCfg.label}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-slate-600">
                      {entry.aiConfidence !== undefined ? `${entry.aiConfidence}%` : '—'}
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-slate-500 truncate">
                        {entry.nurseName}
                        {entry.safetyFlag && <span className="ml-1 text-amber-700">· {entry.safetyFlag}</span>}
                      </div>
                      {isExpanded ? <ChevronUp size={13} className="text-slate-400 shrink-0" /> : <ChevronDown size={13} className="text-slate-400 shrink-0" />}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 bg-slate-50/80 border-t border-slate-100">
                    <div className="grid grid-cols-2 gap-4 mt-3 text-xs">
                      <div className="space-y-1.5">
                        <div className="font-semibold text-slate-700">Event Details</div>
                        <div><span className="text-slate-500">Staff: </span>{entry.nurseName} ({entry.nurseId})</div>
                        <div><span className="text-slate-500">Patient: </span>{entry.patientDisplayId}</div>
                        <div><span className="text-slate-500">Model: </span>{entry.modelVersion || '—'}</div>
                        {entry.aiConfidence !== undefined && (
                          <div><span className="text-slate-500">AI Confidence: </span>{entry.aiConfidence}%</div>
                        )}
                      </div>
                      {isOverride && (
                        <div className="space-y-1.5">
                          <div className="font-semibold text-amber-800">Override Information</div>
                          <div><span className="text-slate-500">Reason: </span>{entry.overrideReason || '—'}</div>
                          {entry.notes && <div><span className="text-slate-500">Notes: </span><em>"{entry.notes}"</em></div>}
                        </div>
                      )}
                      {entry.safetyFlag && (
                        <div className="col-span-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                          <span className="font-semibold text-amber-800">Safety Flag: </span>
                          <span className="text-amber-700">{entry.safetyFlag}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5">
        <Shield size={13} />
        Audit log entries are immutable and cannot be edited or deleted.
      </div>
    </div>
  );
}
