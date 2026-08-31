export type Acuity = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW' | 'PENDING';
export type SafetyStatus = 'NORMAL' | 'VERIFY' | 'URGENT_REVIEW';
export type ArrivalMode = 'walk-in' | 'ambulance' | 'referral' | 'transfer' | 'other';
export type AVPU = 'Alert' | 'Voice' | 'Pain' | 'Unresponsive';
export type AgeGroup = 'PEDIATRIC' | 'ADULT' | 'OLDER_ADULT';
export type Sex = 'Male' | 'Female' | 'Other' | 'Unknown';
export type VitalSource = 'Connected Device' | 'Manual Entry';
export type PatientStatus = 'WAITING' | 'IN_PROGRESS' | 'DISCHARGED' | 'ADMITTED';
export type NurseActionType =
  | 'ACCEPTED'
  | 'OVERRIDE'
  | 'REASSESS_REQUESTED'
  | 'ASSESSMENT_CREATED'
  | 'VITAL_UPDATED'
  | 'OBSERVATION_ADDED';

export type OverrideReason =
  | 'Clinical deterioration'
  | 'Additional observation'
  | 'AI recommendation inconsistent with presentation'
  | 'Missing information'
  | 'Other';

export interface Vitals {
  spo2?: number;
  heartRate?: number;
  respiratoryRate?: number;
  bpSystolic?: number;
  bpDiastolic?: number;
  temperature?: number;
  avpu?: AVPU;
  timestamp: Date;
  source: VitalSource;
}

export interface DangerSign {
  id: string;
  label: string;
  selected: boolean;
}

export interface Patient {
  id: string;
  displayId: string;
  name?: string;
  age: number;
  sex: Sex;
  ageGroup: AgeGroup;
  arrivalMode: ArrivalMode;
  arrivalTime: Date;
  isPregnant?: boolean;
  chiefComplaint: string;
  symptoms: string[];
  dangerSigns: string[];
  vitals: Vitals;
  history: PatientHistory;
  currentAcuity: Acuity;
  aiRecommendation?: AcuityRecommendation;
  safetyStatus: SafetyStatus;
  status: PatientStatus;
  waitingTime: number; // seconds
  reassessmentDue?: Date;
  reassessmentCount: number;
  lastUpdated: Date;
  nurseDecision?: NurseDecision;
  isSimulation: boolean;
  deviceConnected: boolean;
}

export interface PatientHistory {
  available: boolean;
  conditions?: string[];
  medications?: string[];
  allergies?: string[];
  notes?: string;
}

export interface AcuityRecommendation {
  acuity: Acuity;
  confidence: number; // 0-100
  safetyStatus: SafetyStatus;
  safetyFlag?: string;
  dataCompleteness: number; // 0-100
  keyReasons: string[];
  clinicalRules: string[];
  topFactors: FeatureContribution[];
  modelVersion: string;
  timestamp: Date;
  isConservative: boolean;
}

export interface FeatureContribution {
  feature: string;
  value: string;
  impact: 'HIGH' | 'MEDIUM' | 'LOW';
  direction: 'INCREASING' | 'DECREASING';
}

export interface NurseDecision {
  action: NurseActionType;
  finalAcuity: Acuity;
  overrideReason?: OverrideReason;
  overrideNote?: string;
  nurseId: string;
  nurseName: string;
  timestamp: Date;
}

export interface AuditEntry {
  id: string;
  timestamp: Date;
  patientId: string;
  patientDisplayId: string;
  eventType: NurseActionType;
  aiRecommendation?: Acuity;
  aiConfidence?: number;
  safetyFlag?: string;
  nurseAction?: NurseActionType;
  finalAcuity?: Acuity;
  overrideReason?: string;
  modelVersion?: string;
  nurseId: string;
  nurseName: string;
  notes?: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: Date;
  type: NurseActionType | 'AI_ASSESSMENT' | 'VITAL_RECEIVED' | 'ARRIVAL' | 'DEVICE_EVENT';
  title: string;
  description: string;
  acuity?: Acuity;
  confidence?: number;
}

export interface Notification {
  id: string;
  type: 'REASSESSMENT_DUE' | 'VITAL_RECEIVED' | 'PRIORITY_CHANGED' | 'VERIFICATION_REQUIRED' | 'DEVICE_DISCONNECTED';
  message: string;
  patientId: string;
  patientDisplayId: string;
  timestamp: Date;
  read: boolean;
  urgent: boolean;
}

export interface User {
  id: string;
  name: string;
  role: 'Triage Nurse' | 'Clinician' | 'Administrator';
  staffId: string;
  department: string;
}

export interface DeptSummary {
  critical: number;
  high: number;
  moderate: number;
  low: number;
  waiting: number;
  dueForReassessment: number;
  safetyVerificationRequired: number;
  totalPatients: number;
}
