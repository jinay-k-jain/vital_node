import React, { useState } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from './shared/AcuityBadge';
import { Acuity, OverrideReason, Patient } from '../types';
import { X, AlertTriangle, Check } from 'lucide-react';
import clsx from 'clsx';

const OVERRIDE_REASONS: OverrideReason[] = [
  'Clinical deterioration',
  'Additional observation',
  'AI recommendation inconsistent with presentation',
  'Missing information',
  'Other',
];

const ACUITIES: Acuity[] = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW'];

interface Props {
  patient: Patient;
  aiAcuity: Acuity;
  onClose: () => void;
  onOverride: () => void;
}

export function OverrideModal({ patient, aiAcuity, onClose, onOverride }: Props) {
  const { overrideAcuity, user } = useAppStore();
  const [selectedAcuity, setSelectedAcuity] = useState<Acuity>(aiAcuity);
  const [reason, setReason] = useState<OverrideReason | ''>('');
  const [note, setNote] = useState('');
  const [confirming, setConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!reason || !user) return;
    setConfirming(true);
    try {
      await overrideAcuity(patient.id, selectedAcuity, reason as OverrideReason, note, user.id, user.name);
      onOverride();
    } catch {
      window.alert('Could not save the override. The patient queue was not changed.');
    } finally {
      setConfirming(false);
    }
  };
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 bg-amber-50">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-600" />
            <span className="text-sm font-bold text-amber-900">Override AI Recommendation</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-amber-100 text-amber-700">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Patient + AI recommendation */}
          <div className="flex items-center gap-3 bg-slate-50 rounded-xl p-3">
            <div className="flex-1">
              <div className="text-xs text-slate-500 mb-0.5">Patient</div>
              <div className="text-sm font-semibold text-slate-800">{patient.name || patient.displayId}</div>
            </div>
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-0.5">AI recommendation</div>
              <AcuityBadge acuity={aiAcuity} size="sm" />
            </div>
          </div>

          {/* Select new acuity */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">Select new acuity</label>
            <div className="grid grid-cols-2 gap-2">
              {ACUITIES.map(a => (
                <button
                  key={a}
                  onClick={() => setSelectedAcuity(a)}
                  disabled={a === aiAcuity}
                  className={clsx(
                    'flex items-center justify-center gap-2 py-3 rounded-xl border-2 font-bold text-sm transition-colors',
                    a === aiAcuity && 'opacity-40 cursor-not-allowed',
                    selectedAcuity === a && a !== aiAcuity ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 text-slate-700 hover:border-slate-400'
                  )}
                >
                  <AcuityBadge acuity={a} size="sm" showDot />
                </button>
              ))}
            </div>
            {selectedAcuity !== aiAcuity && (
              <div className="flex items-center gap-2 mt-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                <span className="text-xs text-amber-800">
                  AI: <span className="font-bold">{aiAcuity}</span> → Nurse: <span className="font-bold">{selectedAcuity}</span>
                </span>
              </div>
            )}
          </div>

          {/* Override reason */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Override reason <span className="text-red-500">*</span>
            </label>
            <div className="space-y-1.5">
              {OVERRIDE_REASONS.map(r => (
                <button
                  key={r}
                  onClick={() => setReason(r)}
                  className={clsx(
                    'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-sm text-left transition-colors',
                    reason === r ? 'bg-blue-50 border-blue-400 text-blue-800 font-medium' : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                  )}
                >
                  <div className={clsx('w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0',
                    reason === r ? 'border-blue-600 bg-blue-600' : 'border-slate-300')}>
                    {reason === r && <div className="w-2 h-2 rounded-full bg-white" />}
                  </div>
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Optional note */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Additional notes <span className="text-slate-400">(optional)</span>
            </label>
            <textarea
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="Describe clinical observations..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <p className="text-xs text-slate-400">
            This override will be recorded in the audit log with your staff credentials.
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 px-5 pb-5">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!reason || selectedAcuity === aiAcuity || confirming}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-amber-500 hover:bg-amber-600 disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold rounded-xl transition-colors"
          >
            {confirming ? 'Saving...' : (<><Check size={16} />Confirm Override</>)}
          </button>
        </div>
      </div>
    </div>
  );
}
