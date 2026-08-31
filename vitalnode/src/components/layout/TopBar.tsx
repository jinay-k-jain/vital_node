import React, { useState } from 'react';
import { Bell, Wifi, FlaskConical, ChevronDown } from 'lucide-react';
import { useAppStore } from '../../store/appStore';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';

export function TopBar() {
  const { notifications, markNotificationRead, markAllRead, user, demoMode, toggleDemoMode, surgeActive, fetchNotifications } = useAppStore();
  const [showNotif, setShowNotif] = useState(false);
  const unread = notifications.filter(n => !n.read).length;
  const now = new Date();

  // Refresh notifications when dropdown opens
  React.useEffect(() => { if (showNotif) fetchNotifications(); }, [showNotif]);

  return (
    <header className="h-[3.75rem] bg-white border-b border-slate-200 flex items-center px-5 gap-4 shrink-0 z-10">
      {/* Dept + shift */}
      <div className="flex-1">
        <span className="text-base font-semibold text-slate-800">Emergency Department</span>
        <span className="mx-2 text-slate-300">·</span>
        <span className="text-sm text-slate-500">
          {now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
          {' · '}
          {now.getHours() < 8 ? 'Night Shift' : now.getHours() < 16 ? 'Day Shift' : 'Evening Shift'}
        </span>
      </div>

      {/* Surge indicator */}
      {surgeActive && (
        <span className="inline-flex items-center gap-1.5 bg-red-50 border border-red-200 text-red-700 text-sm font-bold px-3 py-1.5 rounded-lg animate-pulse">
          <span className="w-2 h-2 rounded-full bg-red-600" />
          SURGE ACTIVE
        </span>
      )}

      {/* Demo mode */}
      <button
        onClick={toggleDemoMode}
        className={clsx(
          'flex items-center gap-2 text-sm font-semibold px-3 py-2 rounded-lg border transition-colors',
          demoMode
            ? 'bg-violet-50 border-violet-300 text-violet-700'
            : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300'
        )}
      >
        <FlaskConical size={14} />
        {demoMode ? 'DEMO MODE' : 'Demo'}
      </button>

      {/* Connection */}
      <div className="flex items-center gap-1.5 text-sm text-green-700">
        <Wifi size={15} />
        <span className="hidden sm:inline">Connected</span>
      </div>

      {/* Notifications */}
      <div className="relative">
        <button
          onClick={() => setShowNotif(!showNotif)}
          className="relative p-2.5 rounded-lg hover:bg-slate-100 text-slate-600"
          aria-label={`Notifications (${unread} unread)`}
        >
          <Bell size={19} />
          {unread > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center leading-none">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </button>

        {showNotif && (
          <div className="absolute right-0 top-full mt-1 w-88 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden" style={{ width: '22rem' }}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <span className="text-sm font-semibold text-slate-800">Notifications</span>
              {unread > 0 && (
                <button onClick={markAllRead} className="text-sm text-blue-600 hover:underline">
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto scrollbar-thin">
              {notifications.length === 0 ? (
                <div className="px-4 py-6 text-center text-sm text-slate-400">No notifications</div>
              ) : (
                notifications.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => { markNotificationRead(n.id); setShowNotif(false); }}
                    className={clsx(
                      'w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition-colors',
                      !n.read && 'bg-blue-50'
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {n.urgent && <span className="w-2 h-2 rounded-full bg-red-500 mt-1.5 shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className={clsx('text-sm leading-snug', n.read ? 'text-slate-600' : 'text-slate-900 font-medium')}>
                          {n.message}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {formatDistanceToNow(n.timestamp, { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Staff */}
      <div className="flex items-center gap-2.5 cursor-pointer px-2.5 py-2 rounded-lg hover:bg-slate-50">
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-sm font-bold">
          {user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || 'N'}
        </div>
        <div className="hidden sm:block">
          <div className="text-sm font-semibold text-slate-800 leading-none">{user?.name || 'Staff'}</div>
          <div className="text-xs text-slate-500 leading-none mt-0.5">{user?.role}</div>
        </div>
        <ChevronDown size={13} className="text-slate-400" />
      </div>
    </header>
  );
}
