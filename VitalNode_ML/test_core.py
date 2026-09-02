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

"""
terminal output shown in video : 

venv) joy@joy:~/vital_node/VitalNode_ML$ python test_core.py
🏥 VITALNODE SURGE SIMULATION: 15-PATIENT GEMINI PIPELINE 🏥

Initiating 15-Patient Pipeline. Gemini API Rate Limit: 15 RPM (4.1s delay between calls)...
================================================================================

[1/15] 1. Cardiac Arrest (Immediate Danger)
Direct use of automatic function calling (AFC) in Models.generate_content is not recommended. Instead, we recommend to use AFC in Chat.send_message. Similarly, direct use of AFC in Models.generate_content_stream is not recommended. Instead, we recommend to use AFC in Chat.send_message_stream.
Extracted NLP:          Cardiac arrest (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 89.5%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Level 1 Immediate Danger Observed"]
AI Reasoning:           The patient is in active cardiac arrest with a heart rate of zero and no pulse, requiring immediate resuscitative intervention, while there is no medical history available to evaluate compounding risks.

[2/15] 2. Critical Respiratory Failure
Extracted NLP:          Severe respiratory distress (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 99.1%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Severe Hypoxia (SpO2 < 90%)"]
AI Reasoning:           The patient presents with critical respiratory failure characterized by severe hypoxia, cyanosis, and tachycardia, which is highly compounded by their history of severe COPD.

[3/15] 3. Extreme Tachycardia (Arrhythmia)
Extracted NLP:          Symptomatic tachycardia (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 1 (Confidence: 99.3%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Critical Arrhythmia Risk (Extreme HR)"]
AI Reasoning:           The patient's extreme tachycardia of 195 bpm accompanied by dizziness indicates potential hemodynamic compromise, which is severely compounded by their documented history of SVT.

[4/15] 4. Neonatal Sepsis Trap (< 3 months)
Extracted NLP:          Febrile lethargy (Risk: 1)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 2 (Confidence: 72.7%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Neonate Fever Risk (Age <= 3mo, Temp >= 38\u00b0C)"]
AI Reasoning:           The combination of lethargy, fever, and marked tachycardia (HR 145) indicates a high-risk clinical state suggestive of systemic infection or sepsis, while the lack of available medical history provides no compounding risk factors.

[5/15] 5. Hypertensive Emergency (Stroke Risk)
Extracted NLP:          Acute severe headache (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 99.4%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Hypertensive Emergency (BP >= 180/120)"]
AI Reasoning:           A sudden-onset 'worst headache of life' accompanied by blurred vision in a patient with a history of hypertension is highly suspicious for a life-threatening neurological emergency such as a subarachnoid hemorrhage or hypertensive crisis.

[6/15] 6. Pediatric High Fever Risk
Extracted NLP:          Otalgia and fever (Risk: 2)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 2 (Confidence: 82.3%)
Safety Gate Action:     Verify Path: Clinical Protocol Override
Safety Flags Triggered: ["Pediatric High Fever Risk (Temp >= 39\u00b0C)"]
AI Reasoning:           The patient presents with signs of acute otalgia and a high fever of 39.5°C, requiring urgent evaluation for potential otitis media while remaining hemodynamically stable with no known comorbidities.

[7/15] 7. Hypotension / Shock Risk
Extracted NLP:          Syncope and tachycardia (Risk: 1)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 47.7%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Hypotension / Shock Risk (Sys BP < 90)"]
AI Reasoning:           The patient's syncope combined with significant tachycardia (HR 125) represents a high-risk cardiovascular or systemic issue requiring emergent evaluation, with no known historical comorbidities to compound the risk.

[8/15] 8. Extreme Hyperthermia
Extracted NLP:          Altered mental status (Risk: 0)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 49.7%)
Safety Gate Action:     Accept Path
Safety Flags Triggered: ["Extreme Hyperthermia (Temp >= 40\u00b0C)"]
AI Reasoning:           The patient exhibits severe hyperthermia (Temp 40.2°C), tachycardia, and confusion, indicating a life-threatening heat stroke that requires immediate resuscitative cooling.

[9/15] 9. Abdominal Pain with History
Extracted NLP:          RLQ abdominal pain (Risk: 2)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 57.2%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with acute right lower quadrant pain and a low-grade fever, requiring urgent evaluation (ESI 3 equivalent) despite a history of appendectomy ruling out typical appendicitis.

[10/15] 10. Orthopedic Trauma
Extracted NLP:          Deformed upper extremity (Risk: 2)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 38.7%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a suspected extremity fracture requiring multiple emergency department resources including imaging, orthopedic consultation, and pain management, with mild tachycardia likely secondary to pain and no compounding historical risk factors.

[11/15] 11. Standard Adult Fever
Extracted NLP:          Fever and myalgia (Risk: 3)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 50.7%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with stable vital signs and a mild fever typical of a viral syndrome, with no reported medical history to complicate their condition.

[12/15] 12. Mild Allergic Reaction
Extracted NLP:          Localized allergic rash (Risk: 4)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 43.0%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a localized postprandial rash but has completely stable vital signs and no airway compromise, indicating a low-acuity, non-urgent allergic reaction.

[13/15] 13. Standard Pediatric Cold
Extracted NLP:          Cough and rhinorrhea (Risk: 4)
ML Raw Prediction:      ESI 4
Final Fused Acuity:     ESI 4 (Confidence: 60.1%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient exhibits mild upper respiratory symptoms with entirely stable vital signs and has no documented comorbidities, indicating a non-urgent status.

[14/15] 14. Minor Laceration
Extracted NLP:          Finger laceration (Risk: 4)
ML Raw Prediction:      ESI 2
Final Fused Acuity:     ESI 2 (Confidence: 74.4%)
Safety Gate Action:     Accept Path
AI Reasoning:           The patient presents with a minor finger laceration with controlled bleeding and completely stable vital signs, indicating a non-urgent condition with no known compounding history.

[15/15] 15. High Risk with Missing Data
NLP Fallback Triggered: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
Extracted NLP:          Unknown (Risk: 2)
ML Raw Prediction:      ESI 1
Final Fused Acuity:     ESI 1 (Confidence: 49.5%)
Safety Gate Action:     Verify Path: Incomplete Data & Uncertainty
AI Reasoning:           Standard protocol applied due to NLP timeout.

================================================================================
✅ SURGE SIMULATION COMPLETE.


 """