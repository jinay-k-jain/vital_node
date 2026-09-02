import time
from core_engine_gemini import process_patient

print("🏥 VITALNODE ML CORE TEST SUITE (14-FEATURE) 🏥\n")

# Case 1: Unrelated History
patient_1 = {
    "age": 35.0, "sex": 0, "current_hr": 80.0, "current_rr": 16.0, "current_spo2": 98.0, "current_sys_bp": 120.0, "current_dia_bp": 80.0, "temp": 37.0,
    "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
    "complaint": "I have a mild headache.",
    "history_available": 1, "history_text": "Appendectomy in 2015.",
    "immediate_danger": False
}

# Case 2: Crashing Reassessment
patient_2 = {
    "age": 60.0, "sex": 1, "current_hr": 140.0, "current_rr": 24.0, "current_spo2": 89.0, "current_sys_bp": 90.0, "current_dia_bp": 60.0, "temp": 37.5,
    "time_in_queue_mins": 45, "delta_hr": 40.0, "delta_spo2": -8.0,
    "complaint": "I feel very weak and dizzy.",
    "history_available": 0, "history_text": "",
    "immediate_danger": False
}

# Case 3: Compounding Risk
patient_3 = {
    "age": 75.0, "sex": 1, "current_hr": 88.0, "current_rr": 18.0, "current_spo2": 95.0, "current_sys_bp": 130.0, "current_dia_bp": 85.0, "temp": 36.8,
    "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
    "complaint": "My chest feels a bit tight.",
    "history_available": 1, "history_text": "Severe Congestive Heart Failure, Triple Bypass 2020.",
    "immediate_danger": False
}

# Case 4: Pediatric Tachycardia
patient_4 = {
    "age": 3.0, "sex": 0, "current_hr": 175.0, "current_rr": 35.0, "current_spo2": 97.0, "current_sys_bp": 90.0, "current_dia_bp": 55.0, "temp": 38.5,
    "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
    "complaint": "He is crying and feels warm.",
    "history_available": 0, "history_text": "",
    "immediate_danger": False
}

cases = [
    ("Patient 1: Baseline (Unrelated History)", patient_1),
    ("Patient 2: Crashing Reassessment (Deltas)", patient_2),
    ("Patient 3: Relational History Danger", patient_3),
    ("Patient 4: Pediatric Tachycardia (WHO Rules)", patient_4)
]

for name, data in cases:
    print(f"--- {name} ---")
    res = process_patient(patient_id="TEST-0000-UUID", patient=data)
    
    print(f"Extracted Symptom:      {res['extracted_symptom']} (Risk: {res['symptom_risk_score']})")
    print(f"Historical Risk Score:  {res['historical_risk_score']}")
    print(f"ML Raw Prediction:      ESI {res['ml_raw_esi']}")
    print(f"Final Fused Acuity:     ESI {res['final_fused_esi']} (Confidence: {res['confidence']})")
    print(f"Safety Gate Action:     {res['action_path']}")
    print(f"Safety Flags:           {res['safety_flags']}")
    print(f"AI Reasoning:           {res['ai_reasoning']}\n")
    
    print("Waiting 2 seconds for Gemini API rate limits...")
    time.sleep(2)