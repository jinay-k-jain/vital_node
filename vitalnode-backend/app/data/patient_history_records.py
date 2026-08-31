"""
Pre-loaded patient history records.
When a new assessment is created, the system searches this database
by the patient's full name and age range to find matching history.

To add more patients: add entries to PATIENT_HISTORY_RECORDS.
Format:
  - name: patient's name (case-insensitive partial match)
  - age_min / age_max: age range for matching (use same value for exact age)
  - history_text: plain text sent directly to Gemini NLP
  - conditions: list of known conditions
  - medications: list of current medications
  - allergies: list of known allergies
"""

PATIENT_HISTORY_RECORDS = [
    {
        "name": "Rajesh Kumar",
        "age_min": 55, "age_max": 62,
        "history_text": "Hypertension (Stage 2), Type 2 Diabetes Mellitus (on insulin). Mild chronic kidney disease. Previous MI 3 years ago. Smoker (15 pack-years, quit 2 years ago).",
        "conditions": ["Hypertension", "Type 2 Diabetes", "Chronic Kidney Disease", "Prior Myocardial Infarction"],
        "medications": ["Metformin 500mg", "Insulin Glargine", "Amlodipine 10mg", "Aspirin 75mg", "Atorvastatin 40mg"],
        "allergies": ["Penicillin"],
    },
    {
        "name": "Anjali Mehta",
        "age_min": 30, "age_max": 38,
        "history_text": "Bronchial Asthma (moderate persistent). Known atopic dermatitis. Seasonal allergic rhinitis.",
        "conditions": ["Asthma", "Atopic Dermatitis", "Allergic Rhinitis"],
        "medications": ["Salbutamol inhaler PRN", "Fluticasone inhaler", "Cetirizine 10mg"],
        "allergies": ["NSAIDs (aspirin, ibuprofen)", "Dust mites"],
    },
    {
        "name": "Suresh Pillai",
        "age_min": 38, "age_max": 46,
        "history_text": "Hypertension on treatment. History of migraine with aura. No known cardiac disease.",
        "conditions": ["Hypertension", "Migraine with Aura"],
        "medications": ["Telmisartan 40mg", "Topiramate 50mg"],
        "allergies": ["Sulfa drugs"],
    },
    {
        "name": "Saraswati Devi",
        "age_min": 78, "age_max": 86,
        "history_text": "Osteoporosis (on bisphosphonate therapy). Atrial fibrillation (on anticoagulation). Hypertension. History of right hip fracture 2 years ago.",
        "conditions": ["Osteoporosis", "Atrial Fibrillation", "Hypertension"],
        "medications": ["Warfarin 3mg", "Bisoprolol 5mg", "Amlodipine 5mg", "Alendronate"],
        "allergies": [],
    },
    {
        "name": "Prakash Iyer",
        "age_min": 57, "age_max": 65,
        "history_text": "Ischaemic heart disease (stent placed 18 months ago). Hypertension. Dyslipidemia.",
        "conditions": ["Ischaemic Heart Disease", "Post-PCI", "Hypertension", "Dyslipidemia"],
        "medications": ["Aspirin 75mg", "Clopidogrel 75mg", "Atorvastatin 80mg", "Metoprolol 25mg", "Ramipril 5mg"],
        "allergies": [],
    },
    {
        "name": "Fatima Sheikh",
        "age_min": 48, "age_max": 56,
        "history_text": "Hypothyroidism on levothyroxine. Hypertension. History of gestational diabetes.",
        "conditions": ["Hypothyroidism", "Hypertension"],
        "medications": ["Levothyroxine 75mcg", "Losartan 50mg"],
        "allergies": [],
    },
    {
        "name": "Vandana Mishra",
        "age_min": 63, "age_max": 71,
        "history_text": "Hypertension (poorly controlled). Type 2 Diabetes Mellitus. Previous TIA 2 years ago. On antiplatelet therapy.",
        "conditions": ["Hypertension", "Type 2 Diabetes", "Prior TIA"],
        "medications": ["Metformin 1000mg", "Amlodipine 10mg", "Aspirin 75mg", "Atorvastatin 40mg"],
        "allergies": [],
    },
    {
        "name": "Mohan Das",
        "age_min": 45, "age_max": 53,
        "history_text": "Active smoker (20 pack-years). Mild COPD. No known cardiac or metabolic disease.",
        "conditions": ["COPD (Mild)", "Smoking"],
        "medications": ["Tiotropium inhaler"],
        "allergies": [],
    },
    {
        "name": "Sunita Bose",
        "age_min": 51, "age_max": 59,
        "history_text": "Known CAD (coronary artery disease). Stable angina on nitrates. Hypertension.",
        "conditions": ["Coronary Artery Disease", "Stable Angina", "Hypertension"],
        "medications": ["Isosorbide Mononitrate 30mg", "Aspirin 75mg", "Metoprolol 25mg", "Atorvastatin 40mg"],
        "allergies": [],
    },
    {
        "name": "Geeta Nair",
        "age_min": 59, "age_max": 67,
        "history_text": "Type 2 Diabetes Mellitus on insulin. Hypertension. Peripheral neuropathy.",
        "conditions": ["Type 2 Diabetes", "Hypertension", "Peripheral Neuropathy"],
        "medications": ["Insulin Glargine", "Metformin 500mg", "Amlodipine 5mg", "Pregabalin 75mg"],
        "allergies": [],
    },
]


def lookup_patient_history(name: str, age: int) -> dict | None:
    """
    Return a record only when both full name and age range match.
    This deliberately avoids attaching history for a different patient who
    happens to share a name or whose age is entered incorrectly.
    """
    if not name or age <= 0:
        return None

    normalized_name = " ".join(name.casefold().split())

    for record in PATIENT_HISTORY_RECORDS:
        record_name = " ".join(record["name"].casefold().split())
        if (
            normalized_name == record_name
            and record["age_min"] <= age <= record["age_max"]
        ):
            return record

    return None
