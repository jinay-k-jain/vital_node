import React from 'react';
import { Acuity } from '../../types';
import { acuityConfig } from '../../utils/acuity';
import clsx from 'clsx';

interface Props {
  acuity: Acuity;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
  showEsi?: boolean;  // show ESI number prefix (default true)
}

const sizes = {
  sm: 'text-xs px-2 py-0.5 font-bold tracking-wide',
  md: 'text-sm px-2.5 py-1 font-bold tracking-wide',
  lg: 'text-sm px-3 py-1.5 font-bold tracking-wide',
};

export function AcuityBadge({ acuity, size = 'md', showDot = true, showEsi = true }: Props) {
  const cfg = acuityConfig[acuity];
  const esiNum = cfg.esiNumber;

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-md border',
        cfg.bg, cfg.border, cfg.color, sizes[size]
      )}
      title={cfg.esiLabel}
      aria-label={`${cfg.esiLabel} — ${cfg.label}`}
    >
      {showDot && (
        <span className={clsx('inline-block rounded-full shrink-0', cfg.dot, size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2')} />
      )}
      {/* ESI number badge */}
      {showEsi && esiNum > 0 && (
        <span className={clsx(
          'inline-flex items-center justify-center rounded font-extrabold leading-none',
          size === 'sm' ? 'w-4 h-4 text-[10px]' : 'w-5 h-5 text-xs',
          cfg.dot.replace('bg-', 'bg-'), 'text-white'
        )}>
          {esiNum}
        </span>
      )}
      {cfg.label}
    </span>
  );
}
