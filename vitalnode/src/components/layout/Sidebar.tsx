import React, { useState } from 'react';
import {
  LayoutDashboard, Users, PlusCircle, RefreshCw,
  FileText, Zap, Settings, Info, BarChart2, LogOut,
  ChevronLeft, ChevronRight, HeartPulse
} from 'lucide-react';
import clsx from 'clsx';
import { useAppStore } from '../../store/appStore';
import { authApi, setToken } from '../../lib/api';

const navItems = [
  { id: 'dashboard',      label: 'Dashboard',       icon: LayoutDashboard },
  { id: 'queue',          label: 'Patient Queue',    icon: Users },
  { id: 'new-assessment', label: 'New Assessment',   icon: PlusCircle },
  { id: 'reassessment',   label: 'Reassessment',     icon: RefreshCw },
  { id: 'audit',          label: 'Audit Log',        icon: FileText },
  { id: 'surge',          label: 'Surge Mode',       icon: Zap },
  { id: 'analytics',      label: 'Analytics',        icon: BarChart2 },
  { id: 'system',         label: 'System Info',      icon: Info },
  { id: 'settings',       label: 'Settings',         icon: Settings },
];

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen, currentView, setCurrentView, user, logout } = useAppStore();
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <aside className={clsx(
      'h-screen bg-slate-900 flex flex-col transition-all duration-200 shrink-0',
      sidebarOpen ? 'w-72' : 'w-20'
    )}>

      {/* Sign-out confirmation modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-sm mx-4 space-y-5">
            <div className="flex flex-col items-center text-center gap-3">
              <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
                <LogOut size={26} className="text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">Sign out?</h2>
              <p className="text-base text-slate-500">
                Are you sure you want to sign out of VitalNode? Any unsaved changes will be lost.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 py-3 text-base font-semibold border-2 border-slate-200 rounded-xl text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { setShowConfirm(false); authApi.logout().catch(() => {}); setToken(null); logout(); }}
                className="flex-1 py-3 text-base font-semibold bg-red-600 hover:bg-red-700 text-white rounded-xl transition-colors"
              >
                Yes, sign out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Logo */}
      <div className={clsx(
        'flex items-center gap-4 border-b border-slate-800',
        sidebarOpen ? 'px-5 py-6' : 'px-0 py-6 justify-center'
      )}>
        <div className="relative w-11 h-11 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-950/30">
          <div className="absolute inset-1 rounded-xl border border-white/30" />
          <HeartPulse size={22} strokeWidth={2.5} className="relative text-white" />
        </div>
        {sidebarOpen && (
          <div className="overflow-hidden">
            <div className="text-white font-extrabold text-lg tracking-wide leading-none">VITALNODE</div>
            <div className="text-slate-400 text-sm mt-1.5 leading-none truncate">Emergency Triage</div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-thin space-y-1 px-2">
        {navItems.map(({ id, label, icon: Icon }) => {
          const active = currentView === id;
          return (
            <button
              key={id}
              onClick={() => setCurrentView(id)}
              title={!sidebarOpen ? label : undefined}
              className={clsx(
                'w-full flex items-center gap-4 rounded-xl font-semibold transition-all duration-150',
                sidebarOpen ? 'px-4 py-3.5' : 'px-0 py-3.5 justify-center',
                active
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-900/40'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              )}
            >
              <Icon size={22} className="shrink-0" />
              {sidebarOpen && (
                <span className="truncate text-base">{label}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* User info + sign out + collapse */}
      <div className="border-t border-slate-800 p-3 space-y-1">

        {/* User info */}
        {sidebarOpen && user && (
          <div className="flex items-center gap-3 px-3 py-3 rounded-xl bg-slate-800 mb-2">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
              <span className="text-white font-bold text-sm">
                {user.name?.split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold text-white truncate">{user.name}</div>
              <div className="text-xs text-slate-400 truncate mt-0.5">{user.role}</div>
            </div>
          </div>
        )}

        {/* Sign out */}
        <button
          onClick={() => setShowConfirm(true)}
          title="Sign out"
          className={clsx(
            'w-full flex items-center gap-3 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors font-medium',
            sidebarOpen ? 'px-4 py-3' : 'px-0 py-3 justify-center'
          )}
        >
          <LogOut size={20} className="shrink-0" />
          {sidebarOpen && <span className="text-base">Sign out</span>}
        </button>

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          className={clsx(
            'w-full flex items-center rounded-xl text-slate-500 hover:text-white hover:bg-slate-800 transition-colors py-2.5',
            sidebarOpen ? 'px-4 gap-3' : 'px-0 justify-center'
          )}
        >
          {sidebarOpen
            ? <><ChevronLeft size={18} /><span className="text-sm">Collapse</span></>
            : <ChevronRight size={18} />
          }
        </button>

      </div>
    </aside>
  );
}
