import React from 'react';
import clsx from 'clsx';
import { confidenceLabel, confidenceColor } from '../../utils/acuity';

interface Props {
  confidence: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function ConfidenceBar({ confidence, showLabel = true, size = 'md' }: Props) {
  const label = confidenceLabel(confidence);
  const color = confidence >= 85 ? 'bg-green-500' : confidence >= 65 ? 'bg-amber-500' : 'bg-red-500';
  const textColor = confidenceColor(confidence);

  return (
    <div className="flex items-center gap-2">
      <div className={clsx('flex-1 bg-slate-100 rounded-full overflow-hidden', size === 'sm' ? 'h-1.5' : 'h-2')}>
        <div
          className={clsx('h-full rounded-full transition-all duration-300', color)}
          style={{ width: `${confidence}%` }}
          role="progressbar"
          aria-valuenow={confidence}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`AI confidence: ${confidence}%`}
        />
      </div>
      {showLabel && (
        <span className={clsx('font-medium tabular-nums whitespace-nowrap', size === 'sm' ? 'text-xs' : 'text-sm', textColor)}>
          {confidence}% <span className="text-slate-400 font-normal">({label})</span>
        </span>
      )}
    </div>
  );
}
