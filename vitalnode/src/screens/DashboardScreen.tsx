import { useState, useEffect } from 'react';
import { PlusCircle, Search, User, AlertTriangle } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { Patient } from '../types';
import { patientApi, mapPatient } from '../lib/api';

export function DashboardScreen() {
  const { patients, surgePatients, surgeActive, setCurrentView, setSelectedPatient, fetchQueue } = useAppStore();
  const allPatients = surgeActive ? [...patients, ...surgePatients] : patients;

  const [query, setQuery] = useState('');
  const [backendResults, setBackendResults] = useState<Patient[]>([]);
  const [searching, setSearching] = useState(false);

  // Load live queue from backend on mount
  useEffect(() => { fetchQueue(); }, []);

  // Search backend when query changes
  useEffect(() => {
    if (query.trim().length < 1) { setBackendResults([]); return; }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await patientApi.search(query.trim());
        setBackendResults(results.map(mapPatient));
      } catch {
        // fall back to local search
        setBackendResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Merge: backend results first, then local fallback
  const localResults = query.trim().length >= 1
    ? allPatients.filter(p => {
        const q = query.toLowerCase();
        return (
          p.name?.toLowerCase().includes(q) ||
          p.displayId?.toLowerCase().includes(q) ||
          p.chiefComplaint?.toLowerCase().includes(q)
        );
      })
    : [];

  const searchResults = backendResults.length > 0 ? backendResults : localResults;

  const openPatient = (p: Patient) => {
    setSelectedPatient(p.id);
    setCurrentView('patient-detail');
  };

  const acuityColor: Record<string, string> = {
    CRITICAL: 'text-red-600',
    HIGH: 'text-orange-500',
    MODERATE: 'text-amber-500',
    LOW: 'text-green-600',
  };

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50 px-6 py-8">

      {/* Top row: search (center) + New Assessment (right), aligned */}
      <div className="flex items-center gap-4 max-w-7xl mx-auto">
        {/* Spacer left — same width as button so search stays centered */}
        <div className="flex-1" />

        {/* Search bar — centered */}
        <div className="relative w-full max-w-xl">
          <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search by name, patient ID, or complaint…"
            className="w-full pl-12 pr-5 py-3 text-base bg-white border border-slate-200 rounded-2xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900 placeholder:text-slate-400 transition"
            autoFocus
          />
        </div>

        {/* New Assessment — right */}
        <div className="flex-1 flex justify-end">
          <button
            onClick={() => setCurrentView('new-assessment')}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-sm font-semibold px-5 py-3 rounded-2xl shadow-sm transition-colors cursor-pointer whitespace-nowrap"
          >
            <PlusCircle size={18} />
            New Assessment
          </button>
        </div>
      </div>

      {/* Search results */}
      {query.trim().length >= 1 && (
        <div className="max-w-xl mx-auto mt-3 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {searching ? (
            <div className="flex items-center justify-center py-10 gap-2 text-slate-400">
              <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Searching...</p>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-10 text-slate-400">
              <AlertTriangle size={28} className="text-slate-300" />
              <p className="text-sm font-medium">No patient records found for "{query}"</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {searchResults.map(p => (
                <button
                  key={p.id}
                  onClick={() => openPatient(p)}
                  className="w-full flex items-center gap-4 px-5 py-4 hover:bg-slate-50 transition-colors text-left group"
                >
                  <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                    <User size={18} className="text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900 group-hover:text-blue-700 truncate">
                        {p.name || 'Unknown Patient'}
                      </span>
                      <span className="text-xs text-slate-400 font-mono shrink-0">{p.displayId}</span>
                    </div>
                    <p className="text-xs text-slate-500 truncate mt-0.5">{p.chiefComplaint}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <AcuityBadge acuity={p.currentAcuity} size="sm" />
                    <span className={`text-xs font-bold ${acuityColor[p.currentAcuity] ?? 'text-slate-500'}`}>
                      {p.status}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}

