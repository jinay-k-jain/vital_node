/**
 * VitalNode API Client
 * All backend communication goes through this file.
 * The backend URL is configured via VITE_API_URL env variable.
 * Default: http://localhost:8000
 */

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';
const API = `${BASE_URL}/api/v1`;

// ── Token storage ──────────────────────────────────────────────────────────

let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
  if (token) localStorage.setItem('vn_token', token);
  else localStorage.removeItem('vn_token');
}

export function getToken(): string | null {
  if (_token) return _token;
  _token = localStorage.getItem('vn_token');
  return _token;
}

// ── Base fetch wrapper ─────────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isFormData = false,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!isFormData && body) headers['Content-Type'] = 'application/json';

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: isFormData ? (body as FormData) : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let errorMsg = `Request failed: ${res.status}`;
    try {
      const err = await res.json();
      errorMsg = err?.detail?.message || err?.error?.message || errorMsg;
    } catch {
      // ignore parse error
    }
    throw new Error(errorMsg);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

const get  = <T>(path: string)              => request<T>('GET',    path);
const post = <T>(path: string, body?: unknown) => request<T>('POST',   path, body);
const put  = <T>(path: string, body?: unknown) => request<T>('PUT',    path, body);
const del  = <T>(path: string)              => request<T>('DELETE', path);

// ── Auth ───────────────────────────────────────────────────────────────────

export interface BackendUser {
  id: string;
  name: string;
  role: string;
  staffId: string;
  department: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: BackendUser;
}

export const authApi = {
  login: (staffId: string, password: string) =>
    post<LoginResponse>('/auth/login', { staff_id: staffId, password }),

  me: () => get<BackendUser>('/auth/me'),

  logout: () => post<void>('/auth/logout'),
};

// ── Queue ──────────────────────────────────────────────────────────────────

export const queueApi = {
  getQueue: (params?: { acuity?: string; safety_flags?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.acuity) qs.set('acuity', params.acuity);
    if (params?.safety_flags) qs.set('safety_flags', 'true');
    const q = qs.toString();
    return get<any[]>(`/queue${q ? '?' + q : ''}`);
  },

  getSummary: () => get<any>('/queue/summary'),
  complete: (encounterId: string) => post<void>(`/queue/${encounterId}/complete`),
};

// ── Patients ───────────────────────────────────────────────────────────────

export const patientApi = {
  search: (query: string) =>
    get<any[]>(`/patients/search?q=${encodeURIComponent(query)}`),

  assess: (payload: AssessmentPayload) =>
    post<any>('/patients/assess', payload),

  getTimeline: (patientId: string) =>
    get<any[]>(`/patients/${patientId}/timeline`),
};

// ── Assessments ────────────────────────────────────────────────────────────

export const assessmentApi = {
  predict: (assessmentId: string) =>
    post<any>(`/assessments/${assessmentId}/predict`),

  decision: (assessmentId: string, payload: NurseDecisionPayload) =>
    post<any>(`/assessments/${assessmentId}/decision`, payload),

  quality: (assessmentId: string) =>
    get<any>(`/assessments/${assessmentId}/quality`),
};

// ── Reassessments ──────────────────────────────────────────────────────────

export const reassessmentApi = {
  listDue: () => get<any[]>('/reassessments'),

  trigger: (encounterId: string) =>
    post<any>(`/reassessments/${encounterId}`),
};

// ── Notifications ──────────────────────────────────────────────────────────

export const notificationApi = {
  list: (unreadOnly = false) =>
    get<any[]>(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),

  markRead: (id: string) =>
    post<any>(`/notifications/${id}/read`),

  markAllRead: () =>
    post<any>('/notifications/read-all'),
};

// ── Audit ──────────────────────────────────────────────────────────────────

export const auditApi = {
  list: (params?: { event_type?: string; patient_display_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.event_type) qs.set('event_type', params.event_type);
    if (params?.patient_display_id) qs.set('patient_display_id', params.patient_display_id);
    if (params?.limit) qs.set('limit', String(params.limit));
    const q = qs.toString();
    return get<any[]>(`/audit${q ? '?' + q : ''}`);
  },
};

// ── Surge ──────────────────────────────────────────────────────────────────

export const surgeApi = {
  start:  () => post<any>('/surge/start'),
  stop:   () => post<any>('/surge/stop'),
  status: () => get<any>('/surge/status'),
};

export const systemApi = {
  updateReassessmentIntervals: (intervals: { critical: number; high: number; moderate: number; low: number }) =>
    put<{ reassessment_intervals: typeof intervals; rescheduled_encounters: number }>(
      '/system/reassessment-intervals', intervals,
    ),
};

// ── Voice ──────────────────────────────────────────────────────────────────

export const voiceApi = {
  transcribe: async (audioBlob: Blob, filename = 'recording.webm'): Promise<string> => {
    const token = getToken();
    const form = new FormData();
    form.append('audio', audioBlob, filename);

    const res = await fetch(`${API}/voice/transcribe`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });

    if (!res.ok) {
      throw new Error('Voice transcription failed');
    }
    const data = await res.json();
    return data.transcript as string;
  },

  extractSymptoms: (complaintText: string) =>
    post<any>('/voice/extract-symptoms', { complaint_text: complaintText }),
};

// ── Health ─────────────────────────────────────────────────────────────────

export const historyApi = {
  lookup: (name: string, age: number) =>
    get<{ found: boolean; record: any | null }>(`/history/lookup?name=${encodeURIComponent(name)}&age=${age}`),
};

// ── Payload types ──────────────────────────────────────────────────────────

export interface VitalsPayload {
  spo2?: number | null;
  heart_rate?: number | null;
  respiratory_rate?: number | null;
  bp_systolic?: number | null;
  bp_diastolic?: number | null;
  temperature?: number | null;
  avpu?: string | null;
  source: 'Manual Entry' | 'Connected Device';
}

export interface AssessmentPayload {
  age: number;
  sex: string;
  name?: string;
  reassessment_encounter_id?: string;
  arrival_mode: string;
  is_pregnant?: boolean;
  danger_signs: string[];
  none_observed: boolean;
  vitals: VitalsPayload;
  symptoms: string[];
  chief_complaint?: string;
  voice_transcript?: string;
  history: {
    available: boolean;
    conditions?: string[];
    medications?: string[];
    allergies?: string[];
    notes?: string;
  };
}

export interface NurseDecisionPayload {
  action: 'ACCEPTED' | 'OVERRIDE' | 'REASSESS_REQUESTED';
  final_acuity: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
  override_reason?: string;
  override_note?: string;
}

// ── Mapper: backend patient → frontend Patient shape ──────────────────────
// The backend returns camelCase aliases that match the frontend types directly.
// This function just ensures dates are proper Date objects.

export function mapPatient(p: any): any {
  // Normalize vitals — backend REST API returns camelCase, WebSocket may vary
  const rawVitals = p.vitals || {};
  const vitals = {
    spo2:              rawVitals.spo2             ?? null,
    heartRate:         rawVitals.heartRate         ?? rawVitals.heart_rate        ?? null,
    respiratoryRate:   rawVitals.respiratoryRate   ?? rawVitals.respiratory_rate  ?? null,
    bpSystolic:        rawVitals.bpSystolic        ?? rawVitals.bp_systolic       ?? null,
    bpDiastolic:       rawVitals.bpDiastolic       ?? rawVitals.bp_diastolic      ?? null,
    temperature:       rawVitals.temperature       ?? null,
    avpu:              rawVitals.avpu              ?? null,
    source:            rawVitals.source            ?? 'Manual Entry',
    timestamp:         rawVitals.timestamp         ? new Date(rawVitals.timestamp) : new Date(),
  };

  return {
    ...p,
    // Preserve _assessmentId so Accept/Override can call the correct endpoint
    _assessmentId: p._assessmentId || undefined,
    // Ensure all required fields have safe defaults so screens never crash
    name:              p.name             || null,
    age:               p.age              ?? 0,
    sex:               p.sex              || 'Unknown',
    ageGroup:          p.ageGroup         || p.age_group || 'ADULT',
    arrivalMode:       p.arrivalMode      || p.arrival_mode || 'walk-in',
    arrivalTime:       p.arrivalTime      ? new Date(p.arrivalTime)     : new Date(),
    lastUpdated:       p.lastUpdated      ? new Date(p.lastUpdated)     : new Date(),
    reassessmentDue:   p.reassessmentDue  ? new Date(p.reassessmentDue) : undefined,
    chiefComplaint:    p.chiefComplaint   || '',
    symptoms:          Array.isArray(p.symptoms)    ? p.symptoms    : [],
    dangerSigns:       Array.isArray(p.dangerSigns) ? p.dangerSigns : [],
    currentAcuity:     p.currentAcuity   || 'PENDING',
    safetyStatus:      p.safetyStatus    || 'NORMAL',
    status:            p.status          || 'WAITING',
    waitingTime:       p.waitingTime     ?? 0,
    reassessmentCount: p.reassessmentCount ?? 0,
    isSimulation:      p.isSimulation    ?? true,
    deviceConnected:   p.deviceConnected ?? false,
    vitals,
    history: p.history || { available: false },
    aiRecommendation: p.aiRecommendation ? {
      ...p.aiRecommendation,
      timestamp: p.aiRecommendation.timestamp
        ? new Date(p.aiRecommendation.timestamp)
        : new Date(),
      keyReasons:    Array.isArray(p.aiRecommendation.keyReasons)    ? p.aiRecommendation.keyReasons    : [],
      clinicalRules: Array.isArray(p.aiRecommendation.clinicalRules) ? p.aiRecommendation.clinicalRules : [],
      topFactors:    Array.isArray(p.aiRecommendation.topFactors)    ? p.aiRecommendation.topFactors    : [],
    } : undefined,
    nurseDecision: p.nurseDecision ? {
      ...p.nurseDecision,
      timestamp: p.nurseDecision.timestamp
        ? new Date(p.nurseDecision.timestamp)
        : new Date(),
    } : undefined,
  };
}

export const healthApi = {
  check: () => fetch(`${BASE_URL}/health`).then(r => r.json()),
};
