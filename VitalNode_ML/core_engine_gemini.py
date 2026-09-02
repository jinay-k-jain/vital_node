from google import genai
import xgboost as xgb
import pandas as pd
import numpy as np
import json
import re
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL: GEMINI_API_KEY not found in .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)

model = xgb.XGBClassifier()
model.load_model('vitalnode_final_xgboost.json')

# 2. The Single-Shot Unified NLP Extraction
def execute_clinical_nlp(patient):
    """Executes a single API call to prevent rate limiting and reduce latency."""
    history_context = patient['history_text'] if patient['history_available'] == 1 else "No History Available"
    
    prompt = f"""
    You are an expert triage AI. Analyze this patient data:
    COMPLAINT: "{patient['complaint']}"
    HISTORY: "{history_context}"
    VITALS: HR {patient['current_hr']}, SpO2 {patient['current_spo2']}, Temp {patient['temp']}
    
    Calculate the following:
    1. primary_symptom: A 2-3 word clean clinical summary.
    2. symptom_risk: ESI severity equivalent (0=Critical, 4=Non-Urgent).
    3. historical_risk: Comorbidity multiplier IN RELATION to complaint (0=None/Unrelated, 3=Severe/Compounding).
    4. clinical_reasoning: A 1-sentence justification for the extracted risks based on the provided data.
    
    Return ONLY a valid JSON object with the exact keys: primary_symptom, symptom_risk, historical_risk, clinical_reasoning.
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt
        )
        clean = re.sub(r'```(?:json)?\n?(.*?)\n?```', r'\1', response.text, flags=re.DOTALL).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"NLP Fallback Triggered: {e}")
        return {
            "primary_symptom": "Unknown", "symptom_risk": 2, 
            "historical_risk": 0, "clinical_reasoning": "Standard protocol applied due to NLP timeout."
        }

# 3. The Master Decision Fusion Pipeline
def process_patient(patient_id, patient):
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # A. Execute Single-Shot NLP
    nlp_data = execute_clinical_nlp(patient)
    

    # B. Data Completeness
    vitals = [patient['current_hr'], patient['current_rr'], patient['current_spo2'], patient['current_sys_bp'], patient['current_dia_bp'], patient['temp']]
    missing_count = sum(1 for v in vitals if v is None)
    safe_vitals = [v if v is not None else np.nan for v in vitals]

   # C. Comprehensive WHO & ESI Clinical Safety Rules
    clinical_override = None
    flags = []
    
    # Extract vitals for readability (safe_vitals handles None -> np.nan)
    hr = safe_vitals[0]
    rr = safe_vitals[1]
    spo2 = safe_vitals[2]
    sys_bp = safe_vitals[3]
    dia_bp = safe_vitals[4]
    temp = safe_vitals[5]
    age = patient['age']

    # --- LEVEL 1: IMMEDIATE DANGER / RESUSCITATION (Forces ESI 1) ---
    if patient['immediate_danger']:
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

    # --- LEVEL 2: HIGH RISK (Forces ESI 2) ---
    # We only evaluate Level 2 if Level 1 wasn't triggered
    if clinical_override is None:
        
        # 1. Hypertensive Crisis (Using your new Diastolic BP feature)
        if sys_bp >= 180 or dia_bp >= 120:
            clinical_override = 1
            flags.append("Hypertensive Emergency (BP >= 180/120)")
            
        # 2. Adult Hypotension / Shock Risk
        elif age >= 12 and sys_bp < 90:
            clinical_override = 1
            flags.append("Hypotension / Shock Risk (Sys BP < 90)")

        # 3. Pediatric Rules
        elif age < 12:
            if hr > 160:
                clinical_override = 1
                flags.append("Pediatric Tachycardia (HR > 160)")
            # Neonate/Infant Fever: Under 3 months with 38.0°C is an automatic ESI 2
            elif age <= 0.25 and temp >= 38.0:
                clinical_override = 1
                flags.append("Neonate Fever Risk (Age <= 3mo, Temp >= 38°C)")
            # Standard Pediatric Fever
            elif age <= 5 and temp >= 39.0:
                clinical_override = 1
                flags.append("Pediatric High Fever Risk (Temp >= 39°C)")

        # 4. Extreme Temperature (Any Age)
        elif temp >= 40.0:
            clinical_override = 1
            flags.append("Extreme Hyperthermia (Temp >= 40°C)")
        elif temp <= 35.0:
            clinical_override = 1
            flags.append("Extreme Hypothermia (Temp <= 35°C)")
            
        # 5. Standard Hypoxia
        elif spo2 < 92:
            clinical_override = 1
            flags.append("Hypoxia Risk (SpO2 < 92%)")

    # D. XGBoost Inference
    features = pd.DataFrame([{
        'age': patient['age'],
        'sex': patient['sex'],
        'current_hr': safe_vitals[0], 'current_rr': safe_vitals[1], 'current_spo2': safe_vitals[2],
        'current_sys_bp': safe_vitals[3], 'current_dia_bp': safe_vitals[4], 'temp': safe_vitals[5],
        'time_in_queue_mins': patient['time_in_queue_mins'],
        'delta_hr': patient['delta_hr'], 'delta_spo2': patient['delta_spo2'],
        'current_symptom_risk': nlp_data['symptom_risk'],
        'historical_risk_score': nlp_data['historical_risk'] if patient['history_available'] == 1 else np.nan,
        'missing_vitals_count': missing_count
    }])
    
    probs = model.predict_proba(features)[0]
    ml_esi = int(np.argmax(probs))
    confidence = float(np.max(probs) * 100)

    # E. Decision Fusion (Worst-case scenario logic)
    final_esi = ml_esi
    action = "Accept Path"
    
    if clinical_override is not None and clinical_override < ml_esi:
        final_esi = clinical_override
        action = "Verify Path: Clinical Protocol Override"
        
    if missing_count >= 2 and confidence < 75.0:
        action = "Verify Path: Incomplete Data & Uncertainty"

    # F. Database-Ready Output Payload
    return {
        "encounter_id": patient_id,
        "timestamp": timestamp,
        "extracted_symptom": nlp_data['primary_symptom'],
        "symptom_risk_score": nlp_data['symptom_risk'],
        "historical_risk_score": nlp_data['historical_risk'],
        "ml_raw_esi": ml_esi + 1,
        "final_fused_esi": final_esi + 1,
        "confidence": round(confidence, 1),
        "safety_flags": json.dumps(flags), 
        "action_path": action,
        "ai_reasoning": nlp_data['clinical_reasoning']
    }