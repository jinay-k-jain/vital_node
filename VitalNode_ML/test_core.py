import time
from core_engine_gemini import process_patient

print("🏥 VITALNODE SURGE SIMULATION: 15-PATIENT GEMINI PIPELINE 🏥\n")

patients = [
    # --- THE ESI 1 CRITICALS (Resuscitation) ---
    ("1. Cardiac Arrest (Immediate Danger)", {
        "age": 58.0, "sex": 1, "current_hr": 0.0, "current_rr": 0.0, "current_spo2": 0.0, "current_sys_bp": 0.0, "current_dia_bp": 0.0, "temp": 36.0,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Unresponsive, no pulse.", "history_available": 0, "history_text": "", "immediate_danger": True
    }),
    ("2. Critical Respiratory Failure", {
        "age": 72.0, "sex": 0, "current_hr": 130.0, "current_rr": 45.0, "current_spo2": 84.0, "current_sys_bp": 150.0, "current_dia_bp": 95.0, "temp": 37.4,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Gasping for air, cyanotic lips.", "history_available": 1, "history_text": "Severe COPD", "immediate_danger": False
    }),
    ("3. Extreme Tachycardia (Arrhythmia)", {
        "age": 45.0, "sex": 1, "current_hr": 195.0, "current_rr": 24.0, "current_spo2": 95.0, "current_sys_bp": 110.0, "current_dia_bp": 70.0, "temp": 37.0,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Heart is beating out of my chest, dizzy.", "history_available": 1, "history_text": "History of SVT", "immediate_danger": False
    }),

    # --- THE ESI 2 URGENTS (WHO Gate Overrides) ---
    ("4. Neonatal Sepsis Trap (< 3 months)", {
        "age": 0.16, "sex": 0, "current_hr": 145.0, "current_rr": 35.0, "current_spo2": 98.0, "current_sys_bp": 85.0, "current_dia_bp": 50.0, "temp": 38.3,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Lethargic, warm to touch.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("5. Hypertensive Emergency (Stroke Risk)", {
        "age": 62.0, "sex": 1, "current_hr": 88.0, "current_rr": 18.0, "current_spo2": 99.0, "current_sys_bp": 195.0, "current_dia_bp": 125.0, "temp": 37.1,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Worst headache of my life, blurred vision.", "history_available": 1, "history_text": "Hypertension", "immediate_danger": False
    }),
    ("6. Pediatric High Fever Risk", {
        "age": 4.0, "sex": 1, "current_hr": 110.0, "current_rr": 22.0, "current_spo2": 98.0, "current_sys_bp": 105.0, "current_dia_bp": 65.0, "temp": 39.5,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Crying, pulling at ear.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("7. Hypotension / Shock Risk", {
        "age": 28.0, "sex": 0, "current_hr": 125.0, "current_rr": 20.0, "current_spo2": 96.0, "current_sys_bp": 82.0, "current_dia_bp": 55.0, "temp": 36.5,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Fainted, feels weak and cold.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("8. Extreme Hyperthermia", {
        "age": 35.0, "sex": 1, "current_hr": 115.0, "current_rr": 22.0, "current_spo2": 97.0, "current_sys_bp": 118.0, "current_dia_bp": 75.0, "temp": 40.2,
        "time_in_queue_mins": 0, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Heat stroke, confused.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),

    # --- THE ESI 3 MODERATES (ML Territory) ---
    ("9. Abdominal Pain with History", {
        "age": 45.0, "sex": 0, "current_hr": 95.0, "current_rr": 18.0, "current_spo2": 98.0, "current_sys_bp": 135.0, "current_dia_bp": 85.0, "temp": 37.8,
        "time_in_queue_mins": 45, "delta_hr": 5.0, "delta_spo2": 0.0,
        "complaint": "Sharp pain in lower right abdomen.", "history_available": 1, "history_text": "Appendectomy 5 years ago", "immediate_danger": False
    }),
    ("10. Orthopedic Trauma", {
        "age": 22.0, "sex": 1, "current_hr": 105.0, "current_rr": 20.0, "current_spo2": 99.0, "current_sys_bp": 125.0, "current_dia_bp": 80.0, "temp": 36.8,
        "time_in_queue_mins": 15, "delta_hr": 2.0, "delta_spo2": 0.0,
        "complaint": "Fell off bike, visibly deformed arm.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),

    # --- THE ESI 4 & 5 NON-URGENTS (ML Territory) ---
    ("11. Standard Adult Fever", {
        "age": 25.0, "sex": 1, "current_hr": 85.0, "current_rr": 16.0, "current_spo2": 98.0, "current_sys_bp": 120.0, "current_dia_bp": 78.0, "temp": 38.5,
        "time_in_queue_mins": 30, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Flu symptoms, body aches.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("12. Mild Allergic Reaction", {
        "age": 30.0, "sex": 0, "current_hr": 78.0, "current_rr": 16.0, "current_spo2": 99.0, "current_sys_bp": 115.0, "current_dia_bp": 75.0, "temp": 37.0,
        "time_in_queue_mins": 60, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Rash on arms after eating new food. Breathing fine.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("13. Standard Pediatric Cold", {
        "age": 6.0, "sex": 1, "current_hr": 90.0, "current_rr": 20.0, "current_spo2": 99.0, "current_sys_bp": 100.0, "current_dia_bp": 65.0, "temp": 37.5,
        "time_in_queue_mins": 20, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Runny nose and cough for 3 days.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),
    ("14. Minor Laceration", {
        "age": 40.0, "sex": 1, "current_hr": 72.0, "current_rr": 14.0, "current_spo2": 99.0, "current_sys_bp": 125.0, "current_dia_bp": 80.0, "temp": 36.9,
        "time_in_queue_mins": 90, "delta_hr": -2.0, "delta_spo2": 0.0,
        "complaint": "Cut finger while chopping vegetables. Bleeding stopped.", "history_available": 0, "history_text": "", "immediate_danger": False
    }),

    # --- THE EDGE CASE: MISSING VITALS ---
    ("15. High Risk with Missing Data", {
        "age": 75.0, "sex": 0, "current_hr": None, "current_rr": None, "current_spo2": None, "current_sys_bp": None, "current_dia_bp": None, "temp": None,
        "time_in_queue_mins": 5, "delta_hr": 0.0, "delta_spo2": 0.0,
        "complaint": "Severe chest pain radiating to jaw.", "history_available": 1, "history_text": "Two previous heart attacks", "immediate_danger": False
    })
]

print("Initiating 15-Patient Pipeline. Gemini API Rate Limit: 15 RPM (4.1s delay between calls)...\n" + "="*80)

for idx, (name, data) in enumerate(patients, 1):
    print(f"\n[{idx}/15] {name}")
    
    # Process through the unified engine
    res = process_patient(patient_id=f"SURGE-00{idx}", patient=data)
    
    print(f"Extracted NLP:          {res['extracted_symptom']} (Risk: {res['symptom_risk_score']})")
    print(f"ML Raw Prediction:      ESI {res['ml_raw_esi']}")
    print(f"Final Fused Acuity:     ESI {res['final_fused_esi']} (Confidence: {res['confidence']}%)")
    print(f"Safety Gate Action:     {res['action_path']}")
    
    if res['safety_flags'] != "[]":
        print(f"Safety Flags Triggered: {res['safety_flags']}")
        
    print(f"AI Reasoning:           {res['ai_reasoning']}")
    
    # Gemini free tier RPM protection
    if idx < len(patients):
        time.sleep(4.1)

print("\n" + "="*80 + "\n✅ SURGE SIMULATION COMPLETE.")