import time
from core_engine_gemini import process_patient

print("🏥 VITALNODE ML CORE TEST SUITE: PEDIATRIC VS ADULT A/B TEST 🏥\n")

# Case 1: 25-Year-Old Adult with 39°C Fever
# Expected: ML assigns ESI 4 or 5. System accepts it because adults handle fevers well.
patient_adult = {
    "age": 25.0, "sex": 1, "current_hr": 95.0, "current_rr": 18.0, "current_spo2": 98.0, "current_sys_bp": 120.0, "current_dia_bp": 80.0, "temp": 39.0,
    "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
    "complaint": "I have a high fever and feel achy.",
    "history_available": 0, "history_text": "",
    "immediate_danger": False
}

# Case 2: 4-Year-Old Child with 39°C Fever
# Expected: AI might try to assign ESI 4, but WHO gate catches the age+fever combo and forces ESI 2.
patient_child = {
    "age": 4.0, "sex": 1, "current_hr": 95.0, "current_rr": 18.0, "current_spo2": 98.0, "current_sys_bp": 120.0, "current_dia_bp": 80.0, "temp": 39.0,
    "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
    "complaint": "He has a high fever and is crying.",
    "history_available": 0, "history_text": "",
    "immediate_danger": False
}

cases = [
    ("Adult Patient (Age 25) - Standard Triage", patient_adult),
    ("Pediatric Patient (Age 4) - WHO Safety Gate Override", patient_child)
]

for name, data in cases:
    print(f"--- {name} ---")
    res = process_patient(patient_id="TEST-AB-UUID", patient=data)
    
    print(f"Extracted Symptom:      {res['extracted_symptom']} (Risk: {res['symptom_risk_score']})")
    print(f"ML Raw Prediction:      ESI {res['ml_raw_esi']}")
    print(f"Final Fused Acuity:     ESI {res['final_fused_esi']} (Confidence: {res['confidence']}%)")
    print(f"Safety Gate Action:     {res['action_path']}")
    print(f"Safety Flags:           {res['safety_flags']}")
    print(f"AI Reasoning:           {res['ai_reasoning']}\n")
    
    print("Waiting 2.1 seconds for Gemini RPM limits...\n")
    time.sleep(2)