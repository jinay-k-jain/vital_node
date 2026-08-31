import React from 'react';
import clsx from 'clsx';

interface VitalDisplayProps {
  label: string;
  value?: number | string;
  unit?: string;
  source?: string;
  timestamp?: Date;
  alert?: boolean;
  warning?: boolean;
  size?: 'sm' | 'md';
}

export function VitalDisplay({ label, value, unit, source, timestamp, alert, warning, size = 'md' }: VitalDisplayProps) {
  const hasValue = value !== undefined && value !== null;

  return (
    <div className={clsx(
      'rounded-lg border bg-white',
      alert ? 'border-red-200 bg-red-50' : warning ? 'border-amber-200 bg-amber-50' : 'border-slate-200',
      size === 'sm' ? 'p-2.5' : 'p-3'
    )}>
      <div className={clsx('text-slate-500 font-medium mb-1', size === 'sm' ? 'text-xs' : 'text-sm')}>{label}</div>
      {hasValue ? (
        <div className="flex items-baseline gap-1">
          <span className={clsx(
            'font-bold tabular-nums',
            size === 'sm' ? 'text-lg' : 'text-2xl',
            alert ? 'text-red-700' : warning ? 'text-amber-700' : 'text-slate-900'
          )}>
            {value}
          </span>
          {unit && <span className={clsx('text-slate-500', size === 'sm' ? 'text-xs' : 'text-sm')}>{unit}</span>}
        </div>
      ) : (
        <div className={clsx('text-slate-400 italic', size === 'sm' ? 'text-sm' : 'text-base')}>Not recorded</div>
      )}
      {(source || timestamp) && (
        <div className="mt-1.5 flex items-center gap-1.5">
          {source && (
            <span className={clsx(
              'inline-flex items-center gap-1',
              source === 'Connected Device' ? 'text-blue-600' : 'text-slate-400',
              size === 'sm' ? 'text-xs' : 'text-xs'
            )}>
              <span className={clsx(
                'inline-block w-1.5 h-1.5 rounded-full',
                source === 'Connected Device' ? 'bg-blue-500' : 'bg-slate-400'
              )} />
              {source}
            </span>
          )}
          {timestamp && (
            <span className="text-xs text-slate-400">
              {timestamp.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
