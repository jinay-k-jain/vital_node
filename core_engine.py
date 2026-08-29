from google import genai
import xgboost as xgb
import pandas as pd
import numpy as np
import json
import re
from datetime import datetime, timezone

# 1. Configuration & Model Loading (Using the New Unified SDK)
GEMINI_API_KEY = "Your_api_key_here"  # Replace with your actual key or use environment variables
client = genai.Client(api_key=GEMINI_API_KEY) 

model = xgb.XGBClassifier()
model.load_model('vitalnode_production.json')

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
            model='gemini-3.6-flash',
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
    vitals = [patient['current_hr'], patient['current_rr'], patient['current_spo2'], patient['current_sys_bp'], patient['temp']]
    missing_count = sum(1 for v in vitals if v is None)
    safe_vitals = [v if v is not None else np.nan for v in vitals]

    # C. WHO Clinical Safety Rules
    clinical_override = None
    flags = []
    
    if patient['immediate_danger']:
        clinical_override = 0
        flags.append("Level 1 Immediate Danger Observed")
    elif patient['age'] < 12:
        if safe_vitals[0] > 160: 
            clinical_override = 1
            flags.append("Pediatric Tachycardia (HR > 160)")
    else:
        if safe_vitals[2] < 92: 
            clinical_override = 1
            flags.append("Critical Hypoxia (SpO2 < 92%)")

    # D. XGBoost Inference
    features = pd.DataFrame([{
        'age': patient['age'],
        'sex': patient['sex'],
        'current_hr': safe_vitals[0], 'current_rr': safe_vitals[1], 'current_spo2': safe_vitals[2],
        'current_sys_bp': safe_vitals[3], 'temp': safe_vitals[4],
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