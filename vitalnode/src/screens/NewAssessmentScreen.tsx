import { useState, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import { AcuityBadge } from '../components/shared/AcuityBadge';
import { ConfidenceBar } from '../components/shared/ConfidenceBar';
import {
  ChevronRight, ChevronLeft, Mic, MicOff, Plus, X, Check,
  AlertTriangle, Activity, Wifi, WifiOff, Baby, User, BookOpen
} from 'lucide-react';
import clsx from 'clsx';
import { Acuity, AVPU, ArrivalMode, Sex } from '../types';
import { getAgeGroup } from '../utils/acuity';
import { voiceApi, historyApi } from '../lib/api';

const DANGER_SIGNS = [
  { id: 'breathing',    label: 'Breathing Difficulty' },
  { id: 'bleeding',     label: 'Severe Bleeding' },
  { id: 'consciousness',label: 'Altered Consciousness' },
  { id: 'seizure',      label: 'Seizure' },
  { id: 'trauma',       label: 'Major Trauma' },
  { id: 'distress',     label: 'Severe Distress' },
];

const COMPLAINT_CHIPS = [
  'Chest Pain', 'Breathing Difficulty', 'Fever', 'Dizziness', 'Weakness',
  'Abdominal Pain', 'Injury / Trauma', 'Vomiting', 'Unconscious', 'Other',
];

const STEPS = [
  'Patient Information',
  'Danger Signs',
  'Vital Signs',
  'Chief Complaint',
  'Review & Submit',
];

// ---------- Reusable vital input ----------
function VitalInput({
  label, hint, value, onChange, unit, min, max, placeholder, warning, alert,
}: {
  label: string; hint?: string; value: string; onChange: (v: string) => void;
  unit: string; min?: number; max?: number; placeholder?: string;
  warning?: boolean; alert?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1">
        {label}
        {hint && <span className="ml-1 font-normal text-slate-400 text-xs">({hint})</span>}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          min={min}
          max={max}
          className={clsx(
            'flex-1 px-4 py-3 text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500',
            alert   ? 'border-red-400 bg-red-50 text-red-800'
            : warning ? 'border-amber-400 bg-amber-50 text-amber-800'
            : 'border-slate-200 bg-white text-slate-900',
          )}
        />
        <span className="text-sm font-medium text-slate-500 w-10 shrink-0">{unit}</span>
      </div>
      {alert   && <p className="text-sm text-red-600 font-medium mt-1">⚠ Critical range</p>}
      {!alert && warning && <p className="text-sm text-amber-600 font-medium mt-1">Outside normal range</p>}
    </div>
  );
}

// ---------- Main screen ----------
export function NewAssessmentScreen() {
  const { submitAssessment, setSelectedPatient, setCurrentView, patients, selectedPatientId } = useAppStore();
  const reassessingPatientId = (useAppStore.getState() as any)._reassessingPatientId as string | null;
  const [step, setStep] = useState(0);

  // If coming from Reassess, pre-fill from the existing patient
  const reassessPatient = patients.find(p => p.id === reassessingPatientId);
  const isReassessment = !!reassessPatient;

  // Step 0 — Patient Info (pre-fill from existing patient if reassessment)
  const [patientName, setPatientName] = useState(reassessPatient?.name || '');
  const [age, setAge] = useState(reassessPatient?.age?.toString() || '');
  const [sex, setSex] = useState<Sex>((reassessPatient?.sex as Sex) || 'Male');
  const [arrivalMode, setArrivalMode] = useState<ArrivalMode>((reassessPatient?.arrivalMode as ArrivalMode) || 'walk-in');
  const [isPregnant, setIsPregnant] = useState(false);

  // Step 1 — Danger Signs
  const [dangerSigns, setDangerSigns] = useState<Set<string>>(new Set());
  const [noneObserved, setNoneObserved] = useState(false);

  // Step 2 — Vitals
  const [spo2, setSpo2]   = useState('');
  const [hr, setHr]       = useState('');
  const [rr, setRr]       = useState('');
  const [bpSys, setBpSys] = useState('');
  const [bpDia, setBpDia] = useState('');
  const [temp, setTemp]   = useState('');
  const [avpu, setAvpu]   = useState<AVPU>('Alert');
  const [deviceConnected] = useState(false);

  // Step 3 — Complaint
  const [complaint, setComplaint] = useState('');
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [newSymptom, setNewSymptom] = useState('');
  const [voiceError, setVoiceError] = useState('');

  // ageNum needed before useEffect
  const ageNum   = parseInt(age) || 0;
  const ageGroup = getAgeGroup(ageNum);

  // Step 4 — Context (REMOVED — history is now auto-loaded from database)
  // History lookup state
  const [historyFound, setHistoryFound] = useState<any>(null);
  const [historySearching, setHistorySearching] = useState(false);

  // Auto-lookup history when name+age changes
  useEffect(() => {
    if (!patientName.trim() && !ageNum) { setHistoryFound(null); return; }
    setHistorySearching(true);
    const timer = setTimeout(async () => {
      try {
        const result = await historyApi.lookup(patientName.trim(), ageNum);
        setHistoryFound(result.found ? result.record : null);
      } catch {
        setHistoryFound(null);
      } finally {
        setHistorySearching(false);
      }
    }, 600);
    return () => clearTimeout(timer);
  }, [patientName, ageNum]);

  // Step 5 — Assessment
  const [assessing, setAssessing]           = useState(false);
  const [assessmentDone, setAssessmentDone] = useState(false);
  const [assessmentError, setAssessmentError] = useState('');
  const [generatedPatientId, setGeneratedPatientId] = useState('');
  const [generatedPatient, setGeneratedPatient] = useState<any>(null);

  // ageNum and ageGroup already declared above

  const toggleDangerSign = (id: string) => {
    setNoneObserved(false);
    setDangerSigns(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // ── Real voice recording via MediaRecorder + AssemblyAI ──────────────────
  const startRecording = async () => {
    setVoiceError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      const chunks: BlobPart[] = [];
      mr.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setTranscribing(true);
        try {
          const blob = new Blob(chunks, { type: 'audio/webm' });
          const transcript = await voiceApi.transcribe(blob, 'recording.webm');
          setComplaint(transcript);
          // Auto-extract symptoms
          extractSymptomsFromText(transcript);
        } catch {
          setVoiceError('Transcription failed — please type manually.');
        } finally {
          setTranscribing(false);
        }
      };
      mr.start();
      setMediaRecorder(mr);
      setRecording(true);
    } catch {
      setVoiceError('Microphone access denied — please type manually.');
    }
  };

  const stopRecording = () => {
    mediaRecorder?.stop();
    setMediaRecorder(null);
    setRecording(false);
  };

  const handleMicClick = () => {
    if (recording) stopRecording();
    else startRecording();
  };

  const extractSymptomsFromText = (text: string) => {
    if (!text) return;
    const extracted: string[] = [];
    const lower = text.toLowerCase();
    if (lower.includes('chest') || lower.includes('heart')) extracted.push('Chest pain');
    if (lower.includes('breath') || lower.includes('shortness')) extracted.push('Dyspnea');
    if (lower.includes('dizz')) extracted.push('Dizziness');
    if (lower.includes('weak') || lower.includes('tired')) extracted.push('Weakness');
    if (lower.includes('nausea') || lower.includes('vomit')) extracted.push('Nausea');
    if (lower.includes('headache') || lower.includes('head')) extracted.push('Headache');
    if (lower.includes('fever') || lower.includes('hot')) extracted.push('Fever');
    if (lower.includes('pain') && !extracted.includes('Chest pain')) extracted.push('Pain');
    if (extracted.length === 0) extracted.push('Unspecified symptom');
    setSymptoms(prev => [...new Set([...prev, ...extracted])]);
  };

  const extractSymptoms = () => extractSymptomsFromText(complaint);

  const addSymptom = () => {
    if (newSymptom.trim() && !symptoms.includes(newSymptom.trim())) {
      setSymptoms([...symptoms, newSymptom.trim()]);
      setNewSymptom('');
    }
  };

  const removeSymptom = (s: string) => setSymptoms(symptoms.filter(sym => sym !== s));

  const dataCompleteness = () => {
    let score = 0;
    const total = 8;
    if (age) score++;
    if (spo2) score++;
    if (hr) score++;
    if (rr) score++;
    if (bpSys) score++;
    if (temp) score++;
    if (complaint.length > 0) score++;
    if (symptoms.length > 0) score++;
    return Math.round((score / total) * 100);
  };

  const runAIAssessment = async () => {
    setAssessing(true);
    setAssessmentError('');
    try {
      const patient = await submitAssessment({
        age: ageNum,
        sex,
        name: patientName.trim() || undefined,
        reassessment_encounter_id: reassessingPatientId || undefined,
        arrival_mode: arrivalMode,
        is_pregnant: sex === 'Female' ? isPregnant : undefined,
        danger_signs: Array.from(dangerSigns),
        none_observed: noneObserved,
        vitals: {
          spo2:              spo2  ? parseFloat(spo2)  : null,
          heart_rate:        hr    ? parseFloat(hr)    : null,
          respiratory_rate:  rr    ? parseFloat(rr)    : null,
          bp_systolic:       bpSys ? parseFloat(bpSys) : null,
          bp_diastolic:      bpDia ? parseFloat(bpDia) : null,
          temperature:       temp  ? parseFloat(temp)  : null,
          avpu: avpu || null,
          source: deviceConnected ? 'Connected Device' : 'Manual Entry',
        },
        symptoms,
        chief_complaint: complaint || undefined,
        history: { available: false },  // backend auto-looks up from records by name+age
      });

      // Store the patient in both local state AND the global store
      // The local state protects against WebSocket overwriting selectedPatientId
      setGeneratedPatientId(patient.id);
      setGeneratedPatient(patient);
      setSelectedPatient(patient.id);  // set immediately so AI result screen can find it
      setAssessmentDone(true);
    } catch (err: any) {
      setAssessmentError(err.message || 'Assessment failed. Please try again.');
    } finally {
      setAssessing(false);
    }
  };

  const viewResult = () => {
    // Make sure the patient is selected before navigating
    if (generatedPatientId) {
      setSelectedPatient(generatedPatientId);
    }
    setCurrentView('ai-result');
  };

  // ─── Assessment Done screen ───────────────────────────────────────────────
  if (assessmentDone) {
    return (
      <div className="max-w-xl mx-auto p-8 flex flex-col items-center justify-center min-h-96 gap-6">
        <div className="w-20 h-20 rounded-full bg-green-100 flex items-center justify-center">
          <Check size={36} className="text-green-600" />
        </div>
        <div className="text-center">
          <h2 className="text-2xl font-bold text-slate-900">Assessment Complete</h2>
          <p className="text-base text-slate-500 mt-2">AI recommendation is ready for your review.</p>
        </div>
        {generatedPatient?.aiRecommendation && (
          <div className="bg-white border border-slate-200 rounded-2xl p-6 w-full space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold text-slate-700">AI Recommendation</span>
              <AcuityBadge acuity={generatedPatient.aiRecommendation.acuity} />
            </div>
            <ConfidenceBar confidence={generatedPatient.aiRecommendation.confidence} />
            <p className="text-sm text-slate-500">{generatedPatient.aiRecommendation.keyReasons[0]}</p>
          </div>
        )}
        <div className="flex gap-3 w-full">
          <button onClick={viewResult}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base py-3.5 rounded-xl transition-colors">
            Review AI Result
          </button>
          <button onClick={() => { setStep(0); setAssessmentDone(false); }}
            className="px-5 py-3.5 border border-slate-200 rounded-xl text-base text-slate-600 hover:bg-slate-50 transition-colors">
            New Patient
          </button>
        </div>
      </div>
    );
  }

  // ─── Sex option label helper ──────────────────────────────────────────────
  const SEX_OPTIONS: { value: Sex; label: string; sub: string }[] = [
    { value: 'Male',    label: 'Male',    sub: 'M' },
    { value: 'Female',  label: 'Female',  sub: 'F' },
    { value: 'Other',   label: 'Other',   sub: 'O' },
    { value: 'Unknown', label: 'Unknown', sub: '?' },
  ];

  // ─── Main form ────────────────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto px-6 py-8">

      {/* Page heading */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          {isReassessment ? 'Patient Reassessment' : 'New Patient Assessment'}
        </h1>
        <p className="text-base text-slate-500 mt-1">
          {isReassessment
            ? `Updating records for ${reassessPatient?.name || reassessPatient?.displayId}. Enter new vitals and complaint.`
            : 'Complete each section to generate an AI acuity recommendation.'}
        </p>
        {isReassessment && (
          <div className="mt-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-2.5 text-sm text-blue-800 font-medium">
            ↻ Reassessment #{(reassessPatient?.reassessmentCount || 0)} — previous acuity: <strong>{reassessPatient?.currentAcuity}</strong>
          </div>
        )}
      </div>

      {/* Step progress bar */}
      <div className="flex items-center gap-1 mb-2">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className="flex-1 h-2 rounded-full transition-colors"
            style={{ background: i < step ? '#2563eb' : i === step ? '#93c5fd' : '#e2e8f0' }}
          />
        ))}
      </div>
      <p className="text-sm text-slate-500 mb-7">
        Step {step + 1} of {STEPS.length} — <span className="font-semibold text-slate-700">{STEPS[step]}</span>
      </p>

      {/* ── STEP 0: Patient Information ──────────────────────────────── */}
      {step === 0 && (
        <div className="space-y-6">
          <h2 className="text-lg font-bold text-slate-800">Patient Information</h2>

          {/* Patient Name */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Patient Name <span className="font-normal text-slate-400">(optional — leave blank if unknown)</span>
            </label>
            <input
              type="text"
              value={patientName}
              onChange={e => setPatientName(e.target.value)}
              placeholder="e.g. Rajesh Kumar"
              className="w-full px-4 py-3 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* History auto-lookup banner */}
          {(patientName.trim() || ageNum > 0) && (
            <div className={clsx(
              'rounded-xl border px-4 py-3 flex items-start gap-3',
              historySearching ? 'bg-slate-50 border-slate-200' :
              historyFound ? 'bg-green-50 border-green-300' :
              'bg-amber-50 border-amber-200'
            )}>
              <BookOpen size={18} className={clsx(
                'shrink-0 mt-0.5',
                historySearching ? 'text-slate-400' :
                historyFound ? 'text-green-600' : 'text-amber-600'
              )} />
              <div className="flex-1">
                {historySearching && (
                  <p className="text-sm text-slate-500 font-medium">Searching patient records...</p>
                )}
                {!historySearching && historyFound && (
                  <>
                    <p className="text-sm font-bold text-green-800">✅ History found — {historyFound.name}</p>
                    <p className="text-xs text-green-700 mt-1">{historyFound.conditions?.join(', ') || 'See history notes'}</p>
                    <p className="text-xs text-green-600 mt-0.5 italic">This history will be automatically sent to the AI model.</p>
                  </>
                )}
                {!historySearching && !historyFound && (patientName.trim() || ageNum > 0) && (
                  <>
                    <p className="text-sm font-bold text-amber-800">No previous records found</p>
                    <p className="text-xs text-amber-700 mt-0.5">Assessment will proceed without historical context.</p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Age */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Patient Age <span className="font-normal text-slate-400">(in years)</span>
            </label>
            <input
              type="number" value={age} onChange={e => setAge(e.target.value)}
              placeholder="Enter age, e.g. 45" min="0" max="120"
              className="w-full px-4 py-3 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Pediatric / Older Adult notice */}
          {ageGroup === 'PEDIATRIC' && age && (
            <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 px-4 py-3 rounded-xl">
              <Baby size={18} className="text-blue-600 shrink-0" />
              <span className="text-sm font-semibold text-blue-700">
                Pediatric Patient — Age-specific clinical thresholds will apply
              </span>
            </div>
          )}
          {ageGroup === 'OLDER_ADULT' && age && (
            <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 px-4 py-3 rounded-xl">
              <User size={18} className="text-slate-600 shrink-0" />
              <span className="text-sm font-semibold text-slate-700">
                Older Adult — Age context will be factored into assessment
              </span>
            </div>
          )}

          {/* Sex */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Biological Sex</label>
            <div className="grid grid-cols-4 gap-3">
              {SEX_OPTIONS.map(({ value, label, sub }) => (
                <button
                  key={value}
                  onClick={() => setSex(value)}
                  className={clsx(
                    'flex flex-col items-center justify-center py-4 rounded-xl border-2 transition-colors gap-1',
                    sex === value
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                  )}
                >
                  <span className="text-xl font-bold">{sub}</span>
                  <span className="text-xs font-medium">{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Arrival Mode */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Arrival Mode</label>
            <div className="flex flex-wrap gap-2">
              {([
                { value: 'walk-in',   label: 'Walk-in' },
                { value: 'ambulance', label: 'Ambulance' },
                { value: 'referral',  label: 'Referral' },
                { value: 'transfer',  label: 'Transfer' },
                { value: 'other',     label: 'Other' },
              ] as { value: ArrivalMode; label: string }[]).map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => setArrivalMode(value)}
                  className={clsx(
                    'px-5 py-3 text-sm font-semibold rounded-xl border-2 transition-colors',
                    arrivalMode === value
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Pregnancy (conditionally shown) */}
          {sex === 'Female' && ageNum >= 12 && ageNum <= 55 && (
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox" checked={isPregnant} onChange={e => setIsPregnant(e.target.checked)}
                className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-base text-slate-700">Pregnancy possible or confirmed</span>
            </label>
          )}
        </div>
      )}

      {/* ── STEP 1: Danger Signs ─────────────────────────────────────── */}
      {step === 1 && (
        <div className="space-y-5">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Immediate Danger Signs</h2>
            <p className="text-sm text-slate-500 mt-1">
              Select all signs observed during the initial rapid assessment.
            </p>
          </div>

          <div className={clsx(
            'rounded-2xl border-2 p-5 transition-colors',
            dangerSigns.size > 0 ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white',
          )}>
            <div className="grid grid-cols-2 gap-3">
              {DANGER_SIGNS.map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => toggleDangerSign(id)}
                  className={clsx(
                    'flex items-center gap-3 px-4 py-3.5 rounded-xl border-2 text-base font-medium transition-colors text-left',
                    dangerSigns.has(id)
                      ? 'bg-red-100 border-red-400 text-red-800'
                      : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300',
                  )}
                >
                  <div className={clsx(
                    'w-5 h-5 rounded border-2 flex items-center justify-center shrink-0',
                    dangerSigns.has(id) ? 'border-red-600 bg-red-600' : 'border-slate-300',
                  )}>
                    {dangerSigns.has(id) && <Check size={12} className="text-white" />}
                  </div>
                  {label}
                </button>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-200">
              <button
                onClick={() => { setNoneObserved(!noneObserved); setDangerSigns(new Set()); }}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3.5 rounded-xl border-2 text-base font-medium w-full transition-colors',
                  noneObserved
                    ? 'bg-green-100 border-green-400 text-green-800'
                    : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300',
                )}
              >
                <div className={clsx(
                  'w-5 h-5 rounded border-2 flex items-center justify-center shrink-0',
                  noneObserved ? 'border-green-600 bg-green-600' : 'border-slate-300',
                )}>
                  {noneObserved && <Check size={12} className="text-white" />}
                </div>
                None observed — patient appears stable
              </button>
            </div>
          </div>

          {dangerSigns.size > 0 && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-300 px-4 py-3 rounded-xl">
              <AlertTriangle size={18} className="text-red-600 shrink-0" />
              <span className="text-base font-medium text-red-700">
                {dangerSigns.size} danger sign{dangerSigns.size > 1 ? 's' : ''} selected — clinical safety rules will apply
              </span>
            </div>
          )}
        </div>
      )}

      {/* ── STEP 2: Vital Signs ──────────────────────────────────────── */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800">Core Vital Signs</h2>
            <div className={clsx(
              'flex items-center gap-2 text-sm font-medium px-3 py-2 rounded-xl border',
              deviceConnected
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-slate-50 border-slate-200 text-slate-500',
            )}>
              {deviceConnected ? <Wifi size={14} /> : <WifiOff size={14} />}
              {deviceConnected ? 'Device Connected' : 'Manual Entry'}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <VitalInput
              label="Blood Oxygen Saturation (SpO₂)"
              hint="normal: 95–100%"
              value={spo2} onChange={setSpo2}
              unit="%" min={50} max={100} placeholder="e.g. 98"
              warning={!!spo2 && parseFloat(spo2) < 95}
              alert={!!spo2 && parseFloat(spo2) < 90}
            />
            <VitalInput
              label="Heart Rate"
              hint="normal: 60–100 bpm"
              value={hr} onChange={setHr}
              unit="bpm" min={20} max={300} placeholder="e.g. 80"
              warning={!!hr && (parseInt(hr) > 100 || parseInt(hr) < 60)}
              alert={!!hr && (parseInt(hr) > 120 || parseInt(hr) < 50)}
            />
            <VitalInput
              label="Respiratory Rate"
              hint="normal: 12–20 / min"
              value={rr} onChange={setRr}
              unit="/min" min={4} max={60} placeholder="e.g. 16"
              warning={!!rr && (parseInt(rr) > 20 || parseInt(rr) < 12)}
              alert={!!rr && parseInt(rr) > 25}
            />
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">
                Blood Pressure <span className="font-normal text-slate-400">(mmHg)</span>
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number" value={bpSys} onChange={e => setBpSys(e.target.value)}
                  placeholder="Systolic"
                  className={clsx(
                    'flex-1 px-4 py-3 text-base border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500',
                    bpSys && parseInt(bpSys) < 90 ? 'border-red-400 bg-red-50' : 'border-slate-200',
                  )}
                />
                <span className="text-slate-400 font-bold text-lg">/</span>
                <input
                  type="number" value={bpDia} onChange={e => setBpDia(e.target.value)}
                  placeholder="Diastolic"
                  className="flex-1 px-4 py-3 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <p className="text-xs text-slate-400 mt-1">Normal: 90–120 / 60–80 mmHg</p>
            </div>
            <VitalInput
              label="Body Temperature"
              hint="normal: 36.1–37.2 °C"
              value={temp} onChange={setTemp}
              unit="°C" min={32} max={43} placeholder="e.g. 37.0"
              warning={!!temp && parseFloat(temp) > 37.5}
              alert={!!temp && parseFloat(temp) > 39.0}
            />

            {/* AVPU */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">
                Level of Consciousness <span className="font-normal text-slate-400">(AVPU scale)</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {([
                  { value: 'Alert',        label: 'Alert',             sub: 'Fully awake',         color: 'bg-green-600 border-green-600' },
                  { value: 'Voice',        label: 'Responds to Voice', sub: 'Wakes to voice',      color: 'bg-amber-500 border-amber-500' },
                  { value: 'Pain',         label: 'Responds to Pain',  sub: 'Reacts to stimulus',  color: 'bg-orange-500 border-orange-500' },
                  { value: 'Unresponsive', label: 'Unresponsive',      sub: 'No reaction',         color: 'bg-red-600 border-red-600' },
                ] as { value: AVPU; label: string; sub: string; color: string }[]).map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setAvpu(opt.value)}
                    className={clsx(
                      'flex flex-col items-start px-3 py-3 rounded-xl border-2 text-left transition-colors',
                      avpu === opt.value
                        ? `${opt.color} text-white`
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                    )}
                  >
                    <span className="text-sm font-bold">{opt.label}</span>
                    <span className={clsx('text-xs mt-0.5', avpu === opt.value ? 'text-white/80' : 'text-slate-400')}>
                      {opt.sub}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {(!spo2 || !hr || !bpSys) && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
              <span className="font-semibold">Missing critical vitals: </span>
              {[!spo2 && 'SpO₂', !hr && 'Heart Rate', !bpSys && 'Blood Pressure'].filter(Boolean).join(', ')}.
              AI confidence will be reduced.
            </div>
          )}
        </div>
      )}

      {/* ── STEP 3: Chief Complaint ──────────────────────────────────── */}
      {step === 3 && (
        <div className="space-y-5">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Chief Complaint</h2>
            <p className="text-sm text-slate-500 mt-1">Why is the patient presenting today?</p>
          </div>

          {/* Quick-select chips — MULTI SELECT: toggle each chip on/off */}
          <div>
            <p className="text-sm font-semibold text-slate-600 mb-2">Quick Select <span className="font-normal text-slate-400">(select all that apply)</span></p>
            <div className="flex flex-wrap gap-2">
              {COMPLAINT_CHIPS.map(c => {
                const selected = complaint.split(',').map(s => s.trim()).filter(Boolean).includes(c);
                return (
                  <button
                    key={c}
                    onClick={() => {
                      const parts = complaint.split(',').map(s => s.trim()).filter(Boolean);
                      const updated = selected
                        ? parts.filter(p => p !== c)
                        : [...parts, c];
                      setComplaint(updated.join(', '));
                      // Add to symptoms if not already there
                      if (!selected && !symptoms.includes(c)) {
                        setSymptoms(prev => [...prev, c]);
                      }
                    }}
                    className={clsx(
                      'px-4 py-2 text-sm font-medium rounded-full border-2 transition-colors',
                      selected
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                    )}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Free-text + voice */}
          <div>
            <p className="text-sm font-semibold text-slate-600 mb-2">Describe in Detail</p>
            <div className="relative">
              <button
                onClick={handleMicClick}
                disabled={transcribing}
                className={clsx(
                  'absolute right-3 top-3 p-2.5 rounded-xl transition-colors',
                  recording ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-slate-100 text-slate-500 hover:bg-slate-200',
                )}
              >
                {recording ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <textarea
                value={transcribing ? 'Transcribing voice input...' : complaint}
                onChange={e => setComplaint(e.target.value)}
                placeholder="Describe the chief complaint in detail, or tap the microphone for voice input."
                rows={4}
                className="w-full px-4 py-3 pr-14 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>
            {recording    && <p className="text-sm text-red-600 font-medium mt-1 animate-pulse">🔴 Recording — tap mic again to stop</p>}
            {transcribing && <p className="text-sm text-blue-600 font-medium mt-1">⏳ Transcribing via AssemblyAI...</p>}
            {voiceError   && <p className="text-sm text-amber-700 font-medium mt-1">⚠ {voiceError}</p>}
          </div>

          {/* Symptoms */}
          {complaint && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-700">Extracted Symptoms</span>
                <button onClick={extractSymptoms} className="text-sm text-blue-600 hover:underline">
                  Re-extract from complaint
                </button>
              </div>
              {symptoms.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {symptoms.map(s => (
                    <span
                      key={s}
                      className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-200 text-blue-800 text-sm px-3 py-1.5 rounded-full"
                    >
                      {s}
                      <button onClick={() => removeSymptom(s)} className="hover:text-red-600">
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newSymptom}
                  onChange={e => setNewSymptom(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && addSymptom()}
                  placeholder="Add a symptom manually..."
                  className="flex-1 px-4 py-3 text-base border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={addSymptom}
                  className="px-4 py-3 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-600 transition-colors"
                >
                  <Plus size={20} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── STEP 4: Review & Submit ──────────────────────────────────── */}
      {step === 4 && (
        <div className="space-y-5">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Data Quality Review</h2>
            <p className="text-sm text-slate-500 mt-1">
              Review completeness before running the AI assessment.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
            {/* Completeness percentage */}
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold text-slate-700">Overall Data Completeness</span>
              <span className={clsx(
                'text-2xl font-bold tabular-nums',
                dataCompleteness() >= 80 ? 'text-green-700'
                : dataCompleteness() >= 60 ? 'text-amber-700'
                : 'text-red-700',
              )}>
                {dataCompleteness()}%
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-3">
              <div
                className={clsx('h-3 rounded-full transition-all',
                  dataCompleteness() >= 80 ? 'bg-green-500'
                  : dataCompleteness() >= 60 ? 'bg-amber-500'
                  : 'bg-red-500',
                )}
                style={{ width: `${dataCompleteness()}%` }}
              />
            </div>

            {/* Field checklist */}
            <div className="grid grid-cols-2 gap-2 text-sm">
              {[
                { label: 'Age & Sex',           complete: !!(age && sex) },
                { label: 'Vital Signs',          complete: !!(spo2 && hr && rr && bpSys && temp) },
                { label: 'Chief Complaint',      complete: complaint.length > 0 },
                { label: 'Symptoms Listed',      complete: symptoms.length > 0 },
                { label: 'Patient History',      complete: !!historyFound },
                { label: 'Danger Signs Checked', complete: dangerSigns.size > 0 || noneObserved },
              ].map(({ label, complete }) => (
                <div
                  key={label}
                  className={clsx(
                    'flex items-center gap-2.5 px-3 py-3 rounded-xl border',
                    complete ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200',
                  )}
                >
                  <span className={clsx('w-2.5 h-2.5 rounded-full shrink-0', complete ? 'bg-green-500' : 'bg-amber-500')} />
                  <span className={clsx('font-medium', complete ? 'text-green-800' : 'text-amber-800')}>{label}</span>
                  <span className={clsx('ml-auto font-bold text-xs', complete ? 'text-green-700' : 'text-amber-700')}>
                    {complete ? 'Complete' : 'Partial'}
                  </span>
                </div>
              ))}
            </div>

            {dataCompleteness() < 60 && (
              <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <AlertTriangle size={18} className="text-red-600 mt-0.5 shrink-0" />
                <p className="text-sm text-red-700 font-medium">
                  Important information is missing. AI confidence will be reduced and clinical verification will be recommended.
                </p>
              </div>
            )}
          </div>

          <button
            onClick={runAIAssessment}
            disabled={assessing || !age}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold text-base py-4 rounded-xl transition-colors"
          >
            {assessing ? (
              <span className="flex items-center justify-center gap-2">
                <Activity size={18} className="animate-spin" />
                Analysing patient data...
              </span>
            ) : 'Run AI Assessment'}
          </button>
          {assessmentError && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 font-medium">
              ⚠ {assessmentError}
            </div>
          )}
          <p className="text-sm text-slate-400 text-center">
            AI recommendation is advisory only. The nurse's clinical decision is final.
          </p>
        </div>
      )}

      {/* ── Navigation ───────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mt-10 pt-5 border-t border-slate-100">
        <button
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
          className="flex items-center gap-2 px-5 py-3 text-base text-slate-600 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft size={18} />
          Back
        </button>
        {step < STEPS.length - 1 && (
          <button
            onClick={() => setStep(step + 1)}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-base font-semibold rounded-xl transition-colors"
          >
            Continue
            <ChevronRight size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
