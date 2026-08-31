import React from 'react';
import { FlaskConical } from 'lucide-react';

export function SimulationBanner() {
  return (
    <div className="bg-violet-50 border-b border-violet-200 px-4 py-2 flex items-center justify-center gap-2">
      <FlaskConical size={14} className="text-violet-600" />
      <span className="text-sm font-medium text-violet-700">
        Simulation Data — Prototype for Accenture Innovation Challenge 2026
      </span>
    </div>
  );
}
