import React from 'react';
import { SafetyStatus } from '../../types';
import { safetyConfig } from '../../utils/acuity';
import { ShieldAlert, ShieldCheck, ShieldX, LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  status: SafetyStatus;
  size?: 'sm' | 'md';
}

const icons: Record<SafetyStatus, LucideIcon> = {
  NORMAL: ShieldCheck,
  VERIFY: ShieldAlert,
  URGENT_REVIEW: ShieldX,
};

export function SafetyBadge({ status, size = 'md' }: Props) {
  const cfg = safetyConfig[status];
  const Icon = icons[status];
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-md border font-semibold',
        cfg.bg, cfg.border, cfg.color,
        size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
      )}
    >
      <Icon size={size === 'sm' ? 12 : 14} />
      {cfg.label}
    </span>
  );
}
