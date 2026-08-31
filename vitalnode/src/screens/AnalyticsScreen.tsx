import React from 'react';
import { useAppStore } from '../store/appStore';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BarChart2, Users, Clock, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { acuityConfig } from '../utils/acuity';
import clsx from 'clsx';

export function AnalyticsScreen() {
  const { patients, auditLog, surgeActive, surgePatients } = useAppStore();
  const allPatients = surgeActive ? [...patients, ...surgePatients] : patients;

  const acuityData = [
    { name: 'Critical', count: allPatients.filter(p => p.currentAcuity === 'CRITICAL').length, fill: '#dc2626' },
    { name: 'High', count: allPatients.filter(p => p.currentAcuity === 'HIGH').length, fill: '#ea580c' },
    { name: 'Moderate', count: allPatients.filter(p => p.currentAcuity === 'MODERATE').length, fill: '#d97706' },
    { name: 'Low', count: allPatients.filter(p => p.currentAcuity === 'LOW').length, fill: '#16a34a' },
  ];

  const overrides = auditLog.filter(e => e.eventType === 'OVERRIDE').length;
  const acceptances = auditLog.filter(e => e.eventType === 'ACCEPTED').length;
  const reassessments = auditLog.filter(e => e.eventType === 'REASSESS_REQUESTED').length;
  const avgConfidence = allPatients
    .filter(p => p.aiRecommendation)
    .reduce((sum, p) => sum + (p.aiRecommendation?.confidence || 0), 0) /
    Math.max(1, allPatients.filter(p => p.aiRecommendation).length);

  const stats = [
    { label: 'Patients Assessed', value: allPatients.length, icon: Users, color: 'text-blue-600' },
    { label: 'Nurse Overrides', value: overrides, icon: AlertTriangle, color: 'text-amber-600' },
    { label: 'AI Accepted', value: acceptances, icon: CheckCircle, color: 'text-green-600' },
    { label: 'Reassessments', value: reassessments, icon: RefreshCw, color: 'text-blue-600' },
    { label: 'Avg AI Confidence', value: `${Math.round(avgConfidence)}%`, icon: BarChart2, color: 'text-violet-600' },
    {
      label: 'Override Rate',
      value: `${Math.round((overrides / Math.max(1, overrides + acceptances)) * 100)}%`,
      icon: AlertTriangle,
      color: 'text-orange-600'
    },
  ];

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-6xl mx-auto w-full">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Analytics</h1>
        <p className="text-sm text-slate-500 mt-0.5">Operational metrics for this session. Not a clinical effectiveness measure.</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-xs text-amber-800">
        These are prototype operational metrics only. They do not represent clinical outcomes or validate AI performance.
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white border border-slate-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Icon size={14} className={color} />
              <span className="text-xs font-semibold text-slate-500">{label}</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{value}</div>
          </div>
        ))}
      </div>

      {/* Acuity distribution */}
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-4">Patients by Acuity</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={acuityData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {acuityData.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Safety breakdown */}
      <div className="bg-white border border-slate-200 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-slate-800 mb-3">Safety Status Distribution</h3>
        <div className="flex gap-4">
          {[
            { label: 'Normal', count: allPatients.filter(p => p.safetyStatus === 'NORMAL').length, color: 'bg-green-500' },
            { label: 'Verify', count: allPatients.filter(p => p.safetyStatus === 'VERIFY').length, color: 'bg-amber-500' },
            { label: 'Urgent Review', count: allPatients.filter(p => p.safetyStatus === 'URGENT_REVIEW').length, color: 'bg-red-500' },
          ].map(({ label, count, color }) => (
            <div key={label} className="flex items-center gap-2">
              <div className={clsx('w-3 h-3 rounded-full', color)} />
              <span className="text-xs font-medium text-slate-700">{label}</span>
              <span className="text-xs text-slate-500">({count})</span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-400 text-center">
        Prototype data — Accenture Innovation Challenge 2026
      </p>
    </div>
  );
}
