import React, { useState } from 'react';
import { HeartPulse, Lock, User as UserIcon, ChevronDown } from 'lucide-react';
import { useAppStore } from '../store/appStore';
import { authApi, setToken } from '../lib/api';
import { User } from '../types';

export function LoginScreen() {
  const login = useAppStore(s => s.login);
  const [staffId, setStaffId] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<User['role']>('Triage Nurse');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!staffId.trim()) { setError('Staff ID is required.'); return; }
    if (!password.trim()) { setError('Password is required.'); return; }
    setLoading(true);
    setError('');
    try {
      const resp = await authApi.login(staffId.trim(), password);
      setToken(resp.access_token);
      login({
        id: resp.user.id,
        name: resp.user.name,
        role: resp.user.role as User['role'],
        staffId: resp.user.staffId,
        department: resp.user.department,
      });
    } catch (err: any) {
      setError(err.message || 'Invalid staff ID or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between bg-slate-50 overflow-y-auto">
      {/* Top accent line */}
      <div className="h-1.5 bg-blue-600 w-full shrink-0" />

      {/* Main card container */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-10 md:p-14">
        <div className="w-full max-w-2xl space-y-7">
          {/* Brand header */}
          <div className="text-center space-y-3">
            <div className="relative inline-flex items-center justify-center w-18 h-18 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 text-white shadow-lg shadow-blue-500/25 mb-1" style={{ width: 72, height: 72 }}>
              <div className="absolute inset-1.5 rounded-xl border border-white/30" />
              <HeartPulse size={36} strokeWidth={2.5} className="relative" />
            </div>
            <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
              VITALNODE
            </h1>
            <p className="text-base font-medium text-slate-500">
              AI-assisted triage. Human-led care.
            </p>
          </div>

          {/* Login Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-10 sm:p-12 space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Sign in to your account</h2>
              <p className="text-sm text-slate-500 mt-1">Emergency Department Clinical Portal</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Staff ID */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Staff ID / Email
                </label>
                <div className="relative">
                  <UserIcon size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={staffId}
                    onChange={e => setStaffId(e.target.value)}
                    placeholder="e.g. TN-0421"
                    autoComplete="username"
                    className="w-full pl-11 pr-4 py-3 text-base bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900 placeholder:text-slate-400 transition"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    className="w-full pl-11 pr-4 py-3 text-base bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900 placeholder:text-slate-400 transition"
                  />
                </div>
              </div>

              {/* Role Selection */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Clinical Role
                </label>
                <div className="relative">
                  <select
                    value={role}
                    onChange={e => setRole(e.target.value as User['role'])}
                    className="w-full appearance-none pl-4 pr-11 py-3 text-base bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-900 font-medium transition cursor-pointer"
                  >
                    <option>Triage Nurse</option>
                    <option>Clinician</option>
                    <option>Administrator</option>
                  </select>
                  <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {error && (
                <div className="text-sm font-medium text-red-600 bg-red-50 border border-red-200 px-4 py-3 rounded-xl">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white font-semibold text-base py-3.5 px-4 rounded-xl shadow-sm transition duration-150 flex items-center justify-center gap-2 cursor-pointer"
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Signing in...
                  </span>
                ) : (
                  'Sign in securely'
                )}
              </button>
            </form>


          </div>

          {/* Prototype disclaimer */}
          <div className="text-center text-sm text-slate-400 space-y-1">
            <div className="font-medium text-slate-500">Prototype for Accenture Innovation Challenge 2026</div>
            <div>Not clinically validated. Not intended for actual patient care.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
