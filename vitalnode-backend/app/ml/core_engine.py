# """
# VitalNode Core Intelligence Engine v2
# 14-feature XGBoost + Gemini NLP pipeline.

# New in v2:
#   - sex (0=Female, 1=Male) added as feature
#   - current_dia_bp (diastolic blood pressure) added as feature
#   - Output: ESI 1-5 scale (1=most critical, 5=non-urgent)

# API key and model path loaded from environment — never hardcoded.
# """
# import os
# import re
# import json
# import numpy as np
# import pandas as pd
# import xgboost as xgb
# from datetime import datetime, timezone
# from google import genai
# from dotenv import load_dotenv

# load_dotenv()

# # ── Configuration ──────────────────────────────────────────────────────────
# # Load API key — try pydantic settings first (.env file), then env var, then direct
# try:
#     from app.core.config import get_settings as _get_settings
#     _settings = _get_settings()
#     GEMINI_API_KEY = _settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
# except Exception:
#     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# # Cache by the two inputs that affect symptom/history extraction.  This means
# # reassessments do not consume another API request unless either value changes.
# _nlp_cache: dict[tuple[str, str], dict] = {}

# # Use absolute path relative to this file so it works regardless of cwd
# _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# _DEFAULT_MODEL = os.path.join(_THIS_DIR, "vitalnode_final_xgboost.json")
# MODEL_PATH = os.environ.get("MODEL_PATH", _DEFAULT_MODEL)
# # If MODEL_PATH is relative, resolve it against this file's directory
# if not os.path.isabs(MODEL_PATH):
#     MODEL_PATH = os.path.join(_THIS_DIR, os.path.basename(MODEL_PATH))

# # XGBoost model
# model = xgb.XGBClassifier()
# model.load_model(MODEL_PATH)

# # Restore sklearn classifier metadata after loading the XGBoost model.
# # XGBoost 3.x may load the Booster successfully but leave n_classes_
# # unavailable depending on the sklearn compatibility layer.
# _config = json.loads(model.get_booster().save_config())
# model.n_classes_ = int(
#     _config["learner"]["learner_model_param"]["num_class"]
# )

# # XGBoost represents binary classification internally with num_class=0.
# if model.n_classes_ < 2:
#     model.n_classes_ = 2


# def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
#     """Normalise external NLP scores to the ranges used during training."""
#     try:
#         return max(minimum, min(maximum, int(value)))
#     except (TypeError, ValueError):
#         return default


# # ── NLP Extraction ─────────────────────────────────────────────────────────

# def execute_clinical_nlp(patient: dict) -> dict:
#     """
#     Single-shot Gemini API call for clinical NLP extraction.
#     Falls back gracefully if key is missing or call fails.
#     """
#     history_context = (
#         patient["history_text"] if patient.get("history_available") == 1
#         else "No History Available"
#     )

#     stored_extraction = patient.get("nlp_override")
#     if isinstance(stored_extraction, dict):
#         return stored_extraction.copy()

#     if patient.get("use_local_nlp"):
#         return _local_surge_nlp(patient.get("complaint", ""), history_context)

#     cache_key = (str(patient.get("complaint", "")).strip().lower(), history_context.strip().lower())
#     if cache_key in _nlp_cache:
#         return _nlp_cache[cache_key].copy()

#     if not client:
#         return {
#             "primary_symptom": str(patient.get("complaint", "Unknown"))[:40],
#             "symptom_risk": 2,
#             "historical_risk": 0,
#             "clinical_reasoning": "NLP unavailable — Gemini API key not configured.",
#         }

#     prompt = f"""
# You are an expert triage AI. Analyze this patient data:
# COMPLAINT: "{patient.get('complaint', '')}"
# HISTORY: "{history_context}"
# VITALS: HR {patient.get('current_hr')}, SpO2 {patient.get('current_spo2')}, Temp {patient.get('temp')}
# REASSESSMENT CONTEXT: count {patient.get('reassessment_count', 0)}, elapsed since previous vital {patient.get('minutes_since_previous_vital', 'N/A')} minutes, HR change {patient.get('delta_hr', 0)} bpm, SpO2 change {patient.get('delta_spo2', 0)} percentage points.

# Calculate the following:
# 1. primary_symptom: A 2-3 word clean clinical summary.
# 2. symptom_risk: ESI severity equivalent (0=Critical, 4=Non-Urgent).
# 3. historical_risk: Comorbidity multiplier IN RELATION to complaint (0=None/Unrelated, 3=Severe/Compounding).
# 4. clinical_reasoning: A 1-sentence justification for the extracted risks based on the provided data. keep it concise.

# Return ONLY a valid JSON object with the exact keys: primary_symptom, symptom_risk, historical_risk, clinical_reasoning.
# """
#     try:
#         response = client.models.generate_content(
#             model="gemini-3.5-flash",
#             contents=prompt,
#         )
#         clean = re.sub(r"```(?:json)?\n?(.*?)\n?```", r"\1", response.text, flags=re.DOTALL).strip()
#         extracted = json.loads(clean)
#         _nlp_cache[cache_key] = extracted
#         return extracted.copy()
#     except Exception as exc:
#         print(f"NLP Fallback Triggered: {exc}")
#         fallback = {
#             "primary_symptom": "Unknown",
#             "symptom_risk": 2,
#             "historical_risk": 0,
#             "clinical_reasoning": "Standard protocol applied due to NLP timeout.",
#         }
#         _nlp_cache[cache_key] = fallback
#         return fallback.copy()


# def _local_surge_nlp(complaint: str, history: str) -> dict:
#     """Deterministic symptom extraction used only by synthetic surge records."""
#     text = complaint.lower()
#     rules = (
#         (("unconscious", "unresponsive", "seizure"), "Altered consciousness", 0),
#         (("chest pain", "chest tightness"), "Chest pain", 1),
#         (("breathing", "breathless", "dyspnea"), "Breathing difficulty", 1),
#         (("stroke", "facial droop", "weakness"), "Neurological symptoms", 1),
#         (("trauma", "injury", "bleeding", "fall"), "Traumatic injury", 1),
#         (("fever",), "Fever", 2),
#         (("abdominal", "vomiting"), "Abdominal symptoms", 2),
#         (("headache",), "Headache", 2),
#     )
#     symptom, risk = "General symptoms", 2
#     for keywords, candidate, candidate_risk in rules:
#         if any(keyword in text for keyword in keywords):
#             symptom, risk = candidate, candidate_risk
#             break
#     history_risk = 2 if any(word in history.lower() for word in ("heart", "cardiac", "anticoagul", "diabetes")) else 0
#     return {
#         "primary_symptom": symptom,
#         "symptom_risk": risk,
#         "historical_risk": history_risk,
#         "clinical_reasoning": "Deterministic local extraction for synthetic surge simulation.",
#     }


# # ── Master Decision Fusion Pipeline ────────────────────────────────────────

# def process_patient(patient_id: str, patient: dict) -> dict:
#     """
#     Full 14-feature triage pipeline.

#     Input fields:
#       age, sex (0=Female, 1=Male),
#       current_hr, current_rr, current_spo2,
#       current_sys_bp, current_dia_bp, temp,
#       time_in_queue_mins, delta_hr, delta_spo2,
#       complaint, history_available, history_text,
#       immediate_danger

#     Returns ESI on 1-5 scale (1=most critical).
#     """
#     timestamp = datetime.now(timezone.utc).isoformat()

#     # A. NLP extraction
#     nlp_data = execute_clinical_nlp(patient)
#     # Training used symptom risk 0–4 and historical risk 0–3. Gemini is an
#     # external component, so enforce those exact feature domains before the
#     # values are passed to the trained XGBoost model.
#     nlp_data["symptom_risk"] = _bounded_int(nlp_data.get("symptom_risk"), 2, 0, 4)
#     nlp_data["historical_risk"] = _bounded_int(nlp_data.get("historical_risk"), 0, 0, 3)

#     # B. Data completeness (6 vitals)
#     vitals_raw = [
#         patient.get("current_hr"),
#         patient.get("current_rr"),
#         patient.get("current_spo2"),
#         patient.get("current_sys_bp"),
#         patient.get("current_dia_bp"),
#         patient.get("temp"),
#     ]
#     missing_count = sum(1 for v in vitals_raw if v is None)
#     safe_vitals = [v if v is not None else np.nan for v in vitals_raw]

#     # C. Clinical safety rules (override logic)
#     clinical_override = None
#     flags = []

#     if patient.get("immediate_danger"):
#         clinical_override = 0          # ESI index 0 → ESI 1
#         flags.append("Level 1 Immediate Danger Observed")
#     elif patient.get("age", 999) < 12:
#         if not np.isnan(safe_vitals[0]) and safe_vitals[0] > 160:
#             clinical_override = 1       # ESI index 1 → ESI 2
#             flags.append("Pediatric Tachycardia (HR > 160)")
#     else:
#         if not np.isnan(safe_vitals[2]) and safe_vitals[2] < 92:
#             clinical_override = 1
#             flags.append("Critical Hypoxia (SpO2 < 92%)")

#     # D. XGBoost inference — 14 features
#     # sex: 0=Female, 1=Male (numeric, as trained)
#     sex_numeric = patient.get("sex", 0)
#     if isinstance(sex_numeric, str):
#         # Accept "Male"/"Female" string as fallback
#         sex_numeric = 1 if sex_numeric.lower() == "male" else 0

#     features = pd.DataFrame([{
#         "age":                   float(patient.get("age") or 0),
#         "sex":                   float(sex_numeric),
#         "current_hr":            safe_vitals[0],
#         "current_rr":            safe_vitals[1],
#         "current_spo2":          safe_vitals[2],
#         "current_sys_bp":        safe_vitals[3],
#         "current_dia_bp":        safe_vitals[4],
#         "temp":                  safe_vitals[5],
#         "time_in_queue_mins":    float(patient.get("time_in_queue_mins") or 0),
#         "delta_hr":              float(patient.get("delta_hr") or 0),
#         "delta_spo2":            float(patient.get("delta_spo2") or 0),
#         "current_symptom_risk":  nlp_data["symptom_risk"],
#         "historical_risk_score": nlp_data["historical_risk"] if patient.get("history_available") == 1 else np.nan,
#         "missing_vitals_count":  float(missing_count),
#     }])

#     probs = model.predict_proba(features)[0]
#     ml_esi_index = int(np.argmax(probs))        # 0–4 index
#     confidence = float(np.max(probs) * 100)

#     # E. Decision fusion (worst-case logic)
#     final_esi_index = ml_esi_index
#     action = "Accept Path"

#     if clinical_override is not None and clinical_override < ml_esi_index:
#         final_esi_index = clinical_override
#         action = "Verify Path: Clinical Protocol Override"

#     if missing_count >= 2 and confidence < 75.0:
#         action = "Verify Path: Incomplete Data & Uncertainty"

#     # F. Return DB-ready payload (ESI on 1-5 scale)
#     return {
#         "encounter_id":        patient_id,
#         "timestamp":           timestamp,
#         "extracted_symptom":   nlp_data["primary_symptom"],
#         "symptom_risk_score":  nlp_data["symptom_risk"],
#         "historical_risk_score": nlp_data["historical_risk"],
#         "ml_raw_esi":          ml_esi_index + 1,       # 1–5
#         "final_fused_esi":     final_esi_index + 1,    # 1–5
#         "confidence":          round(confidence, 1),
#         "safety_flags":        json.dumps(flags),
#         "action_path":         action,
#         "ai_reasoning":        nlp_data["clinical_reasoning"],
#         "_nlp_extraction":     nlp_data,
#     }

"""
VitalNode Core Intelligence Engine v2
14-feature XGBoost + Gemini NLP pipeline.

New in v2:
  - sex (0=Female, 1=Male) added as feature
  - current_dia_bp (diastolic blood pressure) added as feature
  - Output: ESI 1-5 scale (1=most critical, 5=non-urgent)

API key and model path loaded from environment — never hardcoded.
"""
import os
import re
import json
import numpy as np
import pandas as pd
import xgboost as xgb
from datetime import datetime, timezone
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────
try:
    from app.core.config import get_settings as _get_settings
    _settings = _get_settings()
    GEMINI_API_KEY = _settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

_nlp_cache: dict[tuple[str, str], dict] = {}

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_MODEL = os.path.join(_THIS_DIR, "vitalnode_final_xgboost.json")
MODEL_PATH = os.environ.get("MODEL_PATH", _DEFAULT_MODEL)
if not os.path.isabs(MODEL_PATH):
    MODEL_PATH = os.path.join(_THIS_DIR, os.path.basename(MODEL_PATH))

model = xgb.XGBClassifier()
model.load_model(MODEL_PATH)

_config = json.loads(model.get_booster().save_config())
model.n_classes_ = int(_config["learner"]["learner_model_param"]["num_class"])
if model.n_classes_ < 2:
    model.n_classes_ = 2

def _bounded_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default

# ── NLP Extraction ─────────────────────────────────────────────────────────
def execute_clinical_nlp(patient: dict) -> dict:
    history_context = (
        patient["history_text"] if patient.get("history_available") == 1
        else "No History Available"
    )

    stored_extraction = patient.get("nlp_override")
    if isinstance(stored_extraction, dict):
        return stored_extraction.copy()

    if patient.get("use_local_nlp"):
        return _local_surge_nlp(patient.get("complaint", ""), history_context)

    cache_key = (str(patient.get("complaint", "")).strip().lower(), history_context.strip().lower())
    if cache_key in _nlp_cache:
        return _nlp_cache[cache_key].copy()

    if not client:
        return {
            "primary_symptom": str(patient.get("complaint", "Unknown"))[:40],
            "symptom_risk": 2, "historical_risk": 0,
            "clinical_reasoning": "NLP unavailable — Gemini API key not configured.",
        }

    prompt = f"""
    You are an expert triage AI. Analyze this patient data:
    COMPLAINT: "{patient.get('complaint', '')}"
    HISTORY: "{history_context}"
    VITALS: HR {patient.get('current_hr')}, SpO2 {patient.get('current_spo2')}, Temp {patient.get('temp')}
    
    Calculate the following:
    1. primary_symptom: A 2-3 word clean clinical summary.
    2. symptom_risk: ESI severity equivalent (0=Critical, 4=Non-Urgent).
    3. historical_risk: Comorbidity multiplier IN RELATION to complaint (0=None/Unrelated, 3=Severe/Compounding).
    4. clinical_reasoning: A 1-sentence justification for the extracted risks based on the provided data. keep it concise.
    
    Return ONLY a valid JSON object with the exact keys: primary_symptom, symptom_risk, historical_risk, clinical_reasoning.
    """
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        clean = re.sub(r"```(?:json)?\n?(.*?)\n?```", r"\1", response.text, flags=re.DOTALL).strip()
        extracted = json.loads(clean)
        _nlp_cache[cache_key] = extracted
        return extracted.copy()
    except Exception as exc:
        print(f"NLP Fallback Triggered: {exc}")
        fallback = {
            "primary_symptom": "Unknown", "symptom_risk": 2, "historical_risk": 0,
            "clinical_reasoning": "Standard protocol applied due to NLP timeout.",
        }
        _nlp_cache[cache_key] = fallback
        return fallback.copy()

def _local_surge_nlp(complaint: str, history: str) -> dict:
    text = complaint.lower()
    rules = (
        (("unconscious", "unresponsive", "seizure"), "Altered consciousness", 0),
        (("chest pain", "chest tightness"), "Chest pain", 1),
        (("breathing", "breathless", "dyspnea"), "Breathing difficulty", 1),
        (("stroke", "facial droop", "weakness"), "Neurological symptoms", 1),
        (("trauma", "injury", "bleeding", "fall"), "Traumatic injury", 1),
        (("fever",), "Fever", 2),
        (("abdominal", "vomiting"), "Abdominal symptoms", 2),
        (("headache",), "Headache", 2),
    )
    symptom, risk = "General symptoms", 2
    for keywords, candidate, candidate_risk in rules:
        if any(keyword in text for keyword in keywords):
            symptom, risk = candidate, candidate_risk
            break
    history_risk = 2 if any(word in history.lower() for word in ("heart", "cardiac", "anticoagul", "diabetes")) else 0
    return {
        "primary_symptom": symptom, "symptom_risk": risk, "historical_risk": history_risk,
        "clinical_reasoning": "Deterministic local extraction for synthetic surge simulation.",
    }

# ── Master Decision Fusion Pipeline ────────────────────────────────────────
def process_patient(patient_id: str, patient: dict) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()

    # A. NLP extraction
    nlp_data = execute_clinical_nlp(patient)
    nlp_data["symptom_risk"] = _bounded_int(nlp_data.get("symptom_risk"), 2, 0, 4)
    nlp_data["historical_risk"] = _bounded_int(nlp_data.get("historical_risk"), 0, 0, 3)

    # B. Data completeness
    vitals_raw = [
        patient.get("current_hr"), patient.get("current_rr"), patient.get("current_spo2"),
        patient.get("current_sys_bp"), patient.get("current_dia_bp"), patient.get("temp")
    ]
    missing_count = sum(1 for v in vitals_raw if v is None)
    safe_vitals = [v if v is not None else np.nan for v in vitals_raw]

    # C. Comprehensive WHO & ESI Clinical Safety Rules
    clinical_override = None
    flags = []

    age = float(patient.get("age") or 999)
    hr = safe_vitals[0]
    rr = safe_vitals[1]
    spo2 = safe_vitals[2]
    sys_bp = safe_vitals[3]
    dia_bp = safe_vitals[4]
    temp = safe_vitals[5]

    # LEVEL 1: IMMEDIATE DANGER (Forces ESI 1)
    if patient.get("immediate_danger"):
        clinical_override = 0
        flags.append("Level 1 Immediate Danger Observed")
    elif spo2 < 90:
        clinical_override = 0
        flags.append("Severe Hypoxia (SpO2 < 90%)")
    elif rr < 8 or rr > 40:
        clinical_override = 0
        flags.append("Critical Respiratory Distress (RR < 8 or > 40)")
    elif (age >= 12 and (hr < 40 or hr > 180)) or (age < 12 and hr > 200):
        clinical_override = 0
        flags.append("Critical Arrhythmia Risk (Extreme HR)")

    # LEVEL 2: HIGH RISK (Forces ESI 2)
    if clinical_override is None:
        if sys_bp >= 180 or dia_bp >= 120:
            clinical_override = 1
            flags.append("Hypertensive Emergency (BP >= 180/120)")
        elif age >= 12 and sys_bp < 90:
            clinical_override = 1
            flags.append("Hypotension / Shock Risk (Sys BP < 90)")
        elif age < 12:
            if hr > 160:
                clinical_override = 1
                flags.append("Pediatric Tachycardia (HR > 160)")
            elif age <= 0.25 and temp >= 38.0:
                clinical_override = 1
                flags.append("Neonate Fever Risk (Age <= 3mo, Temp >= 38°C)")
            elif age <= 5 and temp >= 39.0:
                clinical_override = 1
                flags.append("Pediatric High Fever Risk (Temp >= 39°C)")
        elif temp >= 40.0:
            clinical_override = 1
            flags.append("Extreme Hyperthermia (Temp >= 40°C)")
        elif temp <= 35.0:
            clinical_override = 1
            flags.append("Extreme Hypothermia (Temp <= 35°C)")
        elif spo2 < 92:
            clinical_override = 1
            flags.append("Hypoxia Risk (SpO2 < 92%)")

    # D. XGBoost inference
    sex_numeric = patient.get("sex", 0)
    if isinstance(sex_numeric, str):
        sex_numeric = 1 if sex_numeric.lower() == "male" else 0

    features = pd.DataFrame([{
        "age":                   float(patient.get("age") or 0),
        "sex":                   float(sex_numeric),
        "current_hr":            hr,
        "current_rr":            rr,
        "current_spo2":          spo2,
        "current_sys_bp":        sys_bp,
        "current_dia_bp":        dia_bp,
        "temp":                  temp,
        "time_in_queue_mins":    float(patient.get("time_in_queue_mins") or 0),
        "delta_hr":              float(patient.get("delta_hr") or 0),
        "delta_spo2":            float(patient.get("delta_spo2") or 0),
        "current_symptom_risk":  nlp_data["symptom_risk"],
        "historical_risk_score": nlp_data["historical_risk"] if patient.get("history_available") == 1 else np.nan,
        "missing_vitals_count":  float(missing_count),
    }])

    probs = model.predict_proba(features)[0]
    ml_esi_index = int(np.argmax(probs))
    confidence = float(np.max(probs) * 100)

    # E. Decision fusion
    final_esi_index = ml_esi_index
    action = "Accept Path"

    if clinical_override is not None and clinical_override < ml_esi_index:
        final_esi_index = clinical_override
        action = "Verify Path: Clinical Protocol Override"

    if missing_count >= 2 and confidence < 75.0:
        action = "Verify Path: Incomplete Data & Uncertainty"

    # F. Return DB-ready payload
    return {
        "encounter_id":        patient_id,
        "timestamp":           timestamp,
        "extracted_symptom":   nlp_data["primary_symptom"],
        "symptom_risk_score":  nlp_data["symptom_risk"],
        "historical_risk_score": nlp_data["historical_risk"],
        "ml_raw_esi":          ml_esi_index + 1,
        "final_fused_esi":     final_esi_index + 1,
        "confidence":          round(confidence, 1),
        "safety_flags":        json.dumps(flags),
        "action_path":         action,
        "ai_reasoning":        nlp_data["clinical_reasoning"],
        "_nlp_extraction":     nlp_data,
    }