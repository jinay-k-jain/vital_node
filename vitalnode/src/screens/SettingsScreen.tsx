import React, { useState } from 'react';
import { Hospital, Clock, Shield, Bell, Save, CheckCircle2 } from 'lucide-react';
import { systemApi } from '../lib/api';

export function SettingsScreen() {
  const [intervals, setIntervals] = useState({ critical: 5, high: 15, moderate: 30, low: 60 });
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');
  const [error, setError] = useState('');

  const saveIntervals = async () => {
    setSaving(true); setSavedMessage(''); setError('');
    try {
      const response = await systemApi.updateReassessmentIntervals(intervals);
      setSavedMessage(`Timers updated. ${response.rescheduled_encounters} active patient timers were restarted.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update reassessment timers.');
    } finally { setSaving(false); }
  };

  const updateInterval = (key: keyof typeof intervals, value: string) => {
    const minutes = Math.max(1, Math.min(180, Number(value) || 1));
    setIntervals(current => ({ ...current, [key]: minutes }));
  };
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto w-full">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">Hospital configuration and system preferences.</p>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs text-slate-500">
        Configuration changes in this prototype are illustrative. Production settings require administrator authorisation.
      </div>

      {/* Hospital */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Hospital size={15} className="text-slate-600" />
          <h2 className="text-sm font-bold text-slate-800">Hospital Configuration</h2>
        </div>
        <div className="space-y-3">
          {[
            { label: 'Hospital Name', value: 'City Emergency Hospital' },
            { label: 'Department', value: 'Emergency Department' },
            { label: 'Department Code', value: 'ED-001' },
            { label: 'Location', value: 'Mumbai, Maharashtra' },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-xs font-semibold text-slate-600">{label}</span>
              <span className="text-xs text-slate-800">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Reassessment intervals */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={15} className="text-slate-600" />
          <h2 className="text-sm font-bold text-slate-800">Reassessment Intervals</h2>
        </div>
        <p className="text-xs text-slate-500 mb-4">Choose when the system requests reassessment. Saving restarts timers for active patients.</p>
        <div className="space-y-3">
          {[
            { key: 'critical', acuity: 'ESI 1 — CRITICAL', color: 'text-red-700 bg-red-50 border-red-200' },
            { key: 'high', acuity: 'ESI 2 — HIGH', color: 'text-orange-700 bg-orange-50 border-orange-200' },
            { key: 'moderate', acuity: 'ESI 3 — MODERATE', color: 'text-amber-700 bg-amber-50 border-amber-200' },
            { key: 'low', acuity: 'ESI 4/5 — LOW', color: 'text-green-700 bg-green-50 border-green-200' },
          ].map(({ key, acuity, color }) => (
            <div key={acuity} className="flex items-center justify-between">
              <span className={`text-xs font-bold px-2 py-1 rounded border ${color}`}>{acuity}</span>
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-600">
                <input type="number" min="1" max="180" value={intervals[key as keyof typeof intervals]}
                  onChange={event => updateInterval(key as keyof typeof intervals, event.target.value)}
                  className="w-16 px-2 py-1.5 text-right border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
                min
              </label>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 mt-5">
          <button onClick={() => setIntervals({ critical: 30, high: 30, moderate: 30, low: 30 })} className="px-3 py-2 text-xs font-semibold border border-blue-200 text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100">Set all to 30 min</button>
          <button onClick={saveIntervals} disabled={saving} className="flex items-center gap-2 px-3 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 rounded-lg"><Save size={14} /> {saving ? 'Saving…' : 'Save timers'}</button>
        </div>
        {savedMessage && <p className="flex items-center gap-1.5 text-xs text-green-700 mt-3"><CheckCircle2 size={14} />{savedMessage}</p>}
        {error && <p className="text-xs text-red-600 mt-3">{error}</p>}
        <p className="text-xs text-slate-400 mt-3">Prototype setting: changes persist while the backend is running.</p>
      </div>

      {/* Safety thresholds */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={15} className="text-slate-600" />
          <h2 className="text-sm font-bold text-slate-800">Safety Thresholds</h2>
        </div>
        <div className="space-y-2 text-xs text-slate-600">
          {[
            { param: 'SpO₂ Critical', value: '< 90%' },
            { param: 'SpO₂ Warning', value: '< 95%' },
            { param: 'Heart Rate High', value: '> 120 bpm' },
            { param: 'Systolic BP Low', value: '< 90 mmHg' },
            { param: 'Respiratory Rate High', value: '> 25 /min' },
            { param: 'Temperature High', value: '> 39.0°C' },
            { param: 'Min Confidence for auto-accept', value: '85%' },
            { param: 'Data completeness warning', value: '< 70%' },
          ].map(({ param, value }) => (
            <div key={param} className="flex justify-between py-1.5 border-b border-slate-100">
              <span className="text-slate-600">{param}</span>
              <span className="font-semibold text-slate-800 font-mono">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={15} className="text-slate-600" />
          <h2 className="text-sm font-bold text-slate-800">Notifications</h2>
        </div>
        <div className="space-y-3">
          {[
            { label: 'Reassessment due', enabled: true },
            { label: 'New vital reading', enabled: true },
            { label: 'Priority change', enabled: true },
            { label: 'Safety verification required', enabled: true },
            { label: 'Device disconnected', enabled: true },
          ].map(({ label, enabled }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-xs text-slate-700">{label}</span>
              <div className={`w-10 h-5 rounded-full ${enabled ? 'bg-blue-600' : 'bg-slate-200'} flex items-center ${enabled ? 'justify-end' : 'justify-start'} px-0.5`}>
                <div className="w-4 h-4 rounded-full bg-white shadow-sm" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
