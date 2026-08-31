import { create } from 'zustand';
import {
  Patient,
  User,
  Notification,
  AuditEntry,
  Acuity,
  NurseDecision,
  OverrideReason,
} from '../types';

import {
  queueApi,
  patientApi,
  assessmentApi,
  reassessmentApi,
  notificationApi,
  auditApi,
  surgeApi,
  mapPatient,
  AssessmentPayload,
  setToken,
  getToken,
} from '../lib/api';

const STORED_USER_KEY = 'vn_user';

function getStoredUser(): User | null {
  try {
    const raw = localStorage.getItem(STORED_USER_KEY);
    return raw ? JSON.parse(raw) as User : null;
  } catch {
    localStorage.removeItem(STORED_USER_KEY);
    return null;
  }
}

interface AppState {
  // Auth
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
  logout: () => void;

  // Patients — local cache loaded from backend
  patients: Patient[];
  surgePatients: Patient[];

  // Internal patient state
  _pendingPatient: Patient | null;
  _reassessingPatientId: string | null;

  selectedPatientId: string | null;
  setSelectedPatient: (id: string | null) => void;
  addPatient: (patient: Patient) => void;
  updatePatient: (
    id: string,
    updates: Partial<Patient>
  ) => void;

  // Backend actions
  fetchQueue: () => Promise<void>;
  submitAssessment: (
    payload: AssessmentPayload
  ) => Promise<Patient>;
  acceptRecommendation: (
    patientId: string,
    nurseId: string,
    nurseName: string
  ) => Promise<void>;
  overrideAcuity: (
    patientId: string,
    acuity: Acuity,
    reason: OverrideReason,
    note: string,
    nurseId: string,
    nurseName: string
  ) => Promise<void>;
  triggerReassessment: (
    encounterId: string
  ) => Promise<void>;
  dischargePatient: (patientId: string) => Promise<void>;

  // Surge mode
  surgeActive: boolean;
  activateSurge: () => Promise<void>;
  deactivateSurge: () => Promise<void>;

  // Notifications
  notifications: Notification[];
  fetchNotifications: () => Promise<void>;
  addNotification: (
    n: Omit<Notification, 'id' | 'timestamp' | 'read'>
  ) => void;
  markNotificationRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;

  // Audit
  auditLog: AuditEntry[];
  fetchAuditLog: () => Promise<void>;
  addAuditEntry: (
    entry: Omit<AuditEntry, 'id'>
  ) => void;

  // Demo mode
  demoMode: boolean;
  toggleDemoMode: () => void;

  // UI
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  currentView: string;
  setCurrentView: (view: string) => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function mapBackendNotification(n: any): Notification {
  return {
    id: n.id,
    type: n.type,
    message: n.message,
    patientId: n.patientId || n.patient_id || '',
    patientDisplayId:
      n.patientDisplayId || n.patient_display_id || '',
    timestamp: new Date(n.timestamp),
    read: n.read,
    urgent: n.urgent,
  };
}

function mapBackendAudit(e: any): AuditEntry {
  return {
    id: e.id,
    timestamp: new Date(e.timestamp),
    patientId: e.patientId || e.patient_id || '',
    patientDisplayId:
      e.patientDisplayId || e.patient_display_id || '',
    eventType: e.eventType || e.event_type,
    aiRecommendation:
      e.aiRecommendation || e.ai_recommendation,
    aiConfidence:
      e.aiConfidence ?? e.ai_confidence,
    safetyFlag: e.safetyFlag || e.safety_flag,
    nurseAction: e.nurseAction || e.nurse_action,
    finalAcuity: e.finalAcuity || e.final_acuity,
    overrideReason:
      e.overrideReason || e.override_reason,
    modelVersion: e.modelVersion || e.model_version,
    nurseId: e.nurseId || e.nurse_id || '',
    nurseName: e.nurseName || e.nurse_name || '',
    notes: e.notes,
  };
}

// ── Store ──────────────────────────────────────────────────────────────────

export const useAppStore = create<AppState>((set, get) => ({
  // Auth
  user: getStoredUser(),
  isAuthenticated: Boolean(getToken() && getStoredUser()),

  login: (user) => {
    localStorage.setItem(STORED_USER_KEY, JSON.stringify(user));
    set({
      user,
      isAuthenticated: true,
    });

    // Load queue immediately after login
    setTimeout(() => {
      const store = useAppStore.getState();
      store.fetchQueue();
      store.fetchNotifications();
      store.fetchAuditLog();
    }, 100);
  },

  logout: () => {
    setToken(null);
    localStorage.removeItem(STORED_USER_KEY);

    set({
      user: null,
      isAuthenticated: false,
      patients: [],
      auditLog: [],
      _pendingPatient: null,
      _reassessingPatientId: null,
    });
  },

  // Patients
  patients: [],
  _pendingPatient: null,
  _reassessingPatientId: null,
  surgePatients: [],
  selectedPatientId: null,

  setSelectedPatient: (id) =>
    set({
      selectedPatientId: id,
    }),

  addPatient: (patient) =>
    set((s) => ({
      patients: [...s.patients, patient],
    })),

  updatePatient: (id, updates) =>
    set((s) => ({
      patients: s.patients.map((p) =>
        p.id === id
          ? {
              ...p,
              ...updates,
              lastUpdated: new Date(),
            }
          : p
      ),
    })),

  // ── fetchQueue: load live patients from backend ──────────────────────────

  fetchQueue: async () => {
    try {
      const data = await queueApi.getQueue();
      const incoming = data.map(mapPatient);

      // The backend is authoritative for the queue. Replacing this collection
      // ensures completed patients and unaccepted AI recommendations disappear.
      set((state) => {
        const existingMap = new Map(
          state.patients.map((p) => [p.id, p])
        );

        const incomingMap = new Map(
          incoming.map((p) => [p.id, p])
        );

        const updated = incoming.map((fresh) => {
          const existing = existingMap.get(fresh.id);
          return {
            ...fresh,
            aiRecommendation: fresh.aiRecommendation || existing?.aiRecommendation,
            nurseDecision: fresh.nurseDecision || existing?.nurseDecision,
            _assessmentId: (fresh as any)._assessmentId || (existing as any)?._assessmentId,
          };
        });

        return {
          patients: updated,
        };
      });
    } catch {
      // Keep existing data if backend is unreachable
    }
  },

  // ── submitAssessment ─────────────────────────────────────────────────────

  submitAssessment: async (payload) => {
    const data = await patientApi.assess(payload);
    const newPatient = mapPatient(data);

    // Check if this is a reassessment
    const existing = get().patients.find(
      (p) => p.id === payload.reassessment_encounter_id
    );

    if (existing) {
      // Reassessment: update existing patient
      const updatedPatient: Patient = {
        ...existing,
        vitals: newPatient.vitals,
        chiefComplaint:
          newPatient.chiefComplaint ||
          existing.chiefComplaint,
        symptoms:
          newPatient.symptoms?.length
            ? newPatient.symptoms
            : existing.symptoms,
        aiRecommendation: newPatient.aiRecommendation,
        // Keep the existing queue position until the nurse accepts/overrides.
        currentAcuity: existing.currentAcuity,
        safetyStatus: newPatient.safetyStatus,
        reassessmentCount: existing.reassessmentCount || 0,
        lastUpdated: new Date(),
        _assessmentId: (newPatient as any)._assessmentId,
      } as Patient;

      set((s) => ({
        patients: s.patients.map((p) =>
          p.id === existing.id
            ? updatedPatient
            : p
        ),
        _pendingPatient: null,
        _reassessingPatientId: null,
      }));

      return {
        ...updatedPatient,
        id: existing.id,
      };
    }

    // New patient: hold in pending until Accept
    set({
      _pendingPatient: newPatient,
    });

    return newPatient;
  },

  // ── acceptRecommendation ─────────────────────────────────────────────────

  acceptRecommendation: async (
    patientId,
    nurseId,
    nurseName
  ) => {
    const pendingPatient = get()._pendingPatient;

    const patient =
      get().patients.find(
        (p) => p.id === patientId
      ) ||
      (pendingPatient?.id === patientId
        ? pendingPatient
        : null);

    if (!patient?.aiRecommendation) return;

    const assessmentId =
      (patient as any)._assessmentId || patientId;

    try {
      await assessmentApi.decision(assessmentId, {
        action: 'ACCEPTED',
        final_acuity:
          patient.aiRecommendation.acuity as any,
      });
    } catch (error) {
      throw error;
    }

    const decision: NurseDecision = {
      action: 'ACCEPTED',
      finalAcuity: patient.aiRecommendation.acuity,
      nurseId,
      nurseName,
      timestamp: new Date(),
    };

    const updatedPatient = {
      ...patient,
      nurseDecision: decision,
      currentAcuity: patient.aiRecommendation.acuity,
    };

    // Add pending patient to queue after Accept
    set((s) => {
      const existing = s.patients.find(
        (p) => p.id === patientId
      );

      return {
        _pendingPatient: null,
        patients: existing
          ? s.patients.map((p) =>
              p.id === patientId
                ? updatedPatient
                : p
            )
          : [...s.patients, updatedPatient],
      };
    });
    await get().fetchQueue();
  },

  // ── overrideAcuity ───────────────────────────────────────────────────────

  overrideAcuity: async (
    patientId,
    acuity,
    reason,
    note,
    nurseId,
    nurseName
  ) => {
    const pendingPatient = get()._pendingPatient;

    const patient =
      get().patients.find(
        (p) => p.id === patientId
      ) ||
      (pendingPatient?.id === patientId
        ? pendingPatient
        : null);

    if (!patient) return;

    const assessmentId =
      (patient as any)._assessmentId || patientId;

    try {
      await assessmentApi.decision(assessmentId, {
        action: 'OVERRIDE',
        final_acuity: acuity as any,
        override_reason: reason,
        override_note: note,
      });
    } catch (error) {
      throw error;
    }

    const decision: NurseDecision = {
      action: 'OVERRIDE',
      finalAcuity: acuity,
      overrideReason: reason,
      overrideNote: note,
      nurseId,
      nurseName,
      timestamp: new Date(),
    };

    const updatedPatient = {
      ...patient,
      nurseDecision: decision,
      currentAcuity: acuity,
    };

    // Add pending patient to queue or update existing one
    set((s) => {
      const existsInQueue = s.patients.some(
        (p) => p.id === patientId
      );

      return {
        _pendingPatient: null,
        patients: existsInQueue
          ? s.patients.map((p) =>
              p.id === patientId
                ? updatedPatient
                : p
            )
          : [...s.patients, updatedPatient],
      };
    });
    await get().fetchQueue();

    get().addNotification({
      type: 'PRIORITY_CHANGED',
      message: `Priority updated to ${acuity} — ${patient.displayId}`,
      patientId,
      patientDisplayId: patient.displayId,
      urgent:
        acuity === 'CRITICAL' ||
        acuity === 'HIGH',
    });
  },

  // ── triggerReassessment ──────────────────────────────────────────────────

  triggerReassessment: async (encounterId) => {
    const patient = get().patients.find(
      (p) => p.id === encounterId
    );

    // Set this synchronously because the UI navigates to the assessment form
    // immediately after this action is invoked.
    set({ _reassessingPatientId: encounterId });

    try {
      await reassessmentApi.trigger(encounterId);
    } catch {
      // Fall back to local update
    }

    if (patient) {
      get().updatePatient(encounterId, {
        reassessmentCount:
          (patient.reassessmentCount || 0) + 1,
      });
    }

  },

  // ── dischargePatient ─────────────────────────────────────────────────────

  dischargePatient: async (patientId) => {
    await queueApi.complete(patientId);
    set((s) => ({
      patients: s.patients.filter((p) => p.id !== patientId),
    }));
  },

  // ── Surge ────────────────────────────────────────────────────────────────

  surgeActive: false,

  activateSurge: async () => {
    await surgeApi.start();
    await get().fetchQueue();
    set({
      surgeActive: true,
      surgePatients: [],
    });
  },

  deactivateSurge: async () => {
    await surgeApi.stop();
    await get().fetchQueue();

    set({
      surgeActive: false,
      surgePatients: [],
    });
  },

  // ── Notifications ────────────────────────────────────────────────────────

  notifications: [
    {
      id: 'n1',
      type: 'REASSESSMENT_DUE',
      message:
        'Reassessment due — P-10241 (Rajesh Kumar)',
      patientId: 'p001',
      patientDisplayId: 'P-10241',
      timestamp: new Date(),
      read: false,
      urgent: true,
    },
    {
      id: 'n2',
      type: 'VERIFICATION_REQUIRED',
      message:
        'Verification required — P-10248 (Zero-history patient)',
      patientId: 'p008',
      patientDisplayId: 'P-10248',
      timestamp: new Date(Date.now() - 2 * 60000),
      read: false,
      urgent: true,
    },
  ],

  fetchNotifications: async () => {
    try {
      const data = await notificationApi.list();

      set({
        notifications: data.map(
          mapBackendNotification
        ),
      });
    } catch {
      // Keep local notifications
    }
  },

  addNotification: (n) =>
    set((s) => ({
      notifications: [
        {
          ...n,
          id: `notif-${Date.now()}`,
          timestamp: new Date(),
          read: false,
        },
        ...s.notifications,
      ].slice(0, 50),
    })),

  markNotificationRead: async (id) => {
    try {
      await notificationApi.markRead(id);
    } catch {
      // Ignore backend failure
    }

    set((s) => ({
      notifications: s.notifications.map((n) =>
        n.id === id
          ? {
              ...n,
              read: true,
            }
          : n
      ),
    }));
  },

  markAllRead: async () => {
    try {
      await notificationApi.markAllRead();
    } catch {
      // Ignore backend failure
    }

    set((s) => ({
      notifications: s.notifications.map((n) => ({
        ...n,
        read: true,
      })),
    }));
  },

  // ── Audit ────────────────────────────────────────────────────────────────

  auditLog: [],

  fetchAuditLog: async () => {
    try {
      const data = await auditApi.list({
        limit: 200,
      });

      set({
        auditLog: data.map(mapBackendAudit),
      });
    } catch {
      // Keep existing audit log
    }
  },

  addAuditEntry: (entry) =>
    set((s) => ({
      auditLog: [
        {
          ...entry,
          id: `audit-${Date.now()}`,
        },
        ...s.auditLog,
      ],
    })),

  // ── Demo mode ────────────────────────────────────────────────────────────

  demoMode: false,

  toggleDemoMode: () =>
    set((s) => ({
      demoMode: !s.demoMode,
    })),

  // ── UI ───────────────────────────────────────────────────────────────────

  sidebarOpen: true,

  setSidebarOpen: (open) =>
    set({
      sidebarOpen: open,
    }),

  currentView: 'dashboard',

  setCurrentView: (view) =>
    set({
      currentView: view,
    }),
}));
