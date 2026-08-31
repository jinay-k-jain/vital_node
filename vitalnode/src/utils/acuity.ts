import { Acuity, SafetyStatus, AgeGroup } from '../types';

export const acuityConfig: Record<Acuity, { label: string; esiLabel: string; esiNumber: number; color: string; bg: string; border: string; dot: string; ring: string }> = {
  CRITICAL: {
    label: 'CRITICAL',
    esiLabel: 'ESI 1 — Immediate',
    esiNumber: 1,
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    dot: 'bg-red-600',
    ring: 'ring-red-200',
  },
  HIGH: {
    label: 'HIGH',
    esiLabel: 'ESI 2 — Emergent',
    esiNumber: 2,
    color: 'text-orange-700',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    dot: 'bg-orange-500',
    ring: 'ring-orange-200',
  },
  MODERATE: {
    label: 'MODERATE',
    esiLabel: 'ESI 3 — Urgent',
    esiNumber: 3,
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
    ring: 'ring-amber-200',
  },
  LOW: {
    label: 'LOW',
    esiLabel: 'ESI 4/5 — Less Urgent',
    esiNumber: 4,
    color: 'text-green-700',
    bg: 'bg-green-50',
    border: 'border-green-200',
    dot: 'bg-green-500',
    ring: 'ring-green-200',
  },
  PENDING: {
    label: 'PENDING',
    esiLabel: 'Pending Assessment',
    esiNumber: 0,
    color: 'text-slate-600',
    bg: 'bg-slate-50',
    border: 'border-slate-200',
    dot: 'bg-slate-400',
    ring: 'ring-slate-200',
  },
};

export const safetyConfig: Record<SafetyStatus, { label: string; color: string; bg: string; border: string }> = {
  NORMAL: { label: 'Normal', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200' },
  VERIFY: { label: 'Verify', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  URGENT_REVIEW: { label: 'Urgent Review', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200' },
};

export const ageGroupLabel: Record<AgeGroup, string> = {
  PEDIATRIC: 'Pediatric',
  ADULT: 'Adult',
  OLDER_ADULT: 'Older Adult',
};

export function getAgeGroup(age: number): AgeGroup {
  if (age < 18) return 'PEDIATRIC';
  if (age >= 65) return 'OLDER_ADULT';
  return 'ADULT';
}

export function formatWaitingTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function formatCountdown(dueDate: Date): { label: string; overdue: boolean; urgent: boolean } {
  const diffMs = dueDate.getTime() - Date.now();
  const diffSecs = Math.floor(diffMs / 1000);
  if (diffSecs < 0) {
    return { label: 'Overdue', overdue: true, urgent: true };
  }
  const m = Math.floor(diffSecs / 60);
  const s = diffSecs % 60;
  const urgent = diffSecs < 180;
  return {
    label: `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`,
    overdue: false,
    urgent,
  };
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 85) return 'High';
  if (confidence >= 65) return 'Moderate';
  return 'Low';
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 85) return 'text-green-700';
  if (confidence >= 65) return 'text-amber-700';
  return 'text-red-700';
}

export function acuityPriority(acuity: Acuity): number {
  const order: Record<Acuity, number> = { CRITICAL: 0, HIGH: 1, MODERATE: 2, LOW: 3, PENDING: 4 };
  return order[acuity] ?? 5;
}

/** Convert ESI number (1-5) to internal Acuity string */
export function esiToAcuity(esi: number): Acuity {
  if (esi <= 1) return 'CRITICAL';
  if (esi === 2) return 'HIGH';
  if (esi === 3) return 'MODERATE';
  return 'LOW';
}

/** Get ESI number from Acuity */
export function acuityToEsi(acuity: Acuity): number {
  return acuityConfig[acuity]?.esiNumber ?? 0;
}
