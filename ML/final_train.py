import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

print("--- TRAINING FINAL XGBOOST MODEL (14-FEATURE ARCHITECTURE) ---")

# 1. Load real hospital data (CDC NHAMCS)
df_raw = pd.read_stata('ed2022-stata(1).dta', convert_categoricals=False)

# Added SEX and BPDIAS to the extraction list
columns_to_keep = ['AGE', 'SEX', 'PULSE', 'RESPR', 'POPCT', 'BPSYS', 'BPDIAS', 'TEMPF', 'IMMEDR']
df = df_raw[columns_to_keep].copy()

# 2. Clean missing data markers
for col in columns_to_keep:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# CDC uses negative numbers (like -9) for blank/unknown data. Convert those to NaN.
df[df < 0] = np.nan

# Keep only valid triage scores (ESI 1 through 5)
df = df[(df['IMMEDR'] >= 1) & (df['IMMEDR'] <= 5)].copy()

# 3. Rename and Standardize Features
df = df.rename(columns={
    'AGE': 'age', 
    'SEX': 'sex', 
    'PULSE': 'current_hr', 
    'RESPR': 'current_rr', 
    'POPCT': 'current_spo2', 
    'BPSYS': 'current_sys_bp',
    'BPDIAS': 'current_dia_bp'
})

# Convert Fahrenheit to Celsius
df['temp'] = ((df['TEMPF'] - 32) * 5.0/9.0).round(1)

# Map CDC's sex encoding (1=Female, 2=Male) to standard 0 (Female) and 1 (Male)
df['sex'] = np.where(df['sex'] == 2, 1, 0)

# 4. ENGINEER THE SYNTHETIC FEATURES (The GenAI & Surge augmentations)
np.random.seed(42)

# Vitals completeness (Now tracking 6 core vitals including diastolic BP)
core_vitals = ['current_hr', 'current_rr', 'current_spo2', 'current_sys_bp', 'current_dia_bp', 'temp']
df['missing_vitals_count'] = df[core_vitals].isna().sum(axis=1)

# Temporal Deltas (Simulating waiting room changes)
df['time_in_queue_mins'] = np.random.randint(0, 120, size=len(df))
df['delta_hr'] = np.where(df['time_in_queue_mins'] > 0, np.random.normal(0, 15, size=len(df)), 0)
df['delta_spo2'] = np.where(df['time_in_queue_mins'] > 0, np.random.normal(0, 2, size=len(df)), 0)

# Symptom Risk & Historical Risk (Simulating the Gemini NLP outputs)
df['current_symptom_risk'] = np.random.choice([0, 1, 2, 3, 4], size=len(df), p=[0.1, 0.2, 0.4, 0.2, 0.1])
df['history_available'] = np.random.choice([1, 0], size=len(df), p=[0.6, 0.4])
df['historical_risk_score'] = np.where(
    df['history_available'] == 1, 
    np.random.choice([0, 1, 2, 3], size=len(df), p=[0.4, 0.3, 0.2, 0.1]), 
    np.nan
)

# 5. TARGET MAPPING & LOGIC INJECTION
# XGBoost needs classes 0 to 4 (representing ESI 1 to 5)
df['acuity'] = df['IMMEDR'] - 1 

# TEACH THE MODEL: If heart rate spikes by 30+ OR SpO2 drops by 5+ while waiting, force Acuity to 0 (Critical)
df.loc[(df['delta_hr'] > 30) | (df['delta_spo2'] < -5), 'acuity'] = 0 

# TEACH THE MODEL: If Historical Risk is 3 (Severe) and Symptom Risk is 1 (Emergent), force Acuity to 0 or 1
df.loc[(df['historical_risk_score'] == 3) & (df['current_symptom_risk'] <= 1), 'acuity'] = np.minimum(df['acuity'], 1)

df['acuity'] = df['acuity'].astype(int)

# 6. TRAIN THE MODEL
# The final 14 features matching the core_engine.py array
features = [
    'age', 'sex', 'current_hr', 'current_rr', 'current_spo2', 'current_sys_bp', 'current_dia_bp', 'temp', 
    'time_in_queue_mins', 'delta_hr', 'delta_spo2', 
    'current_symptom_risk', 'historical_risk_score', 'missing_vitals_count'
]

X = df[features]
y = df['acuity']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Initialize XGBoost - missing=np.nan is critical for handling incomplete triage vitals
final_model = xgb.XGBClassifier(
    objective='multi:softprob', 
    num_class=5, 
    eval_metric='mlogloss', 
    use_label_encoder=False, 
    missing=np.nan
)

final_model.fit(X_train, y_train)

# Save the artifact for the web devs
final_model.save_model('vitalnode_final_xgboost.json')
print("✅ Saved 'vitalnode_final_xgboost.json'")

# Print diagnostics
y_pred = final_model.predict(X_test)
print("\nClassification Report (14-Feature Architecture):")
print(classification_report(y_test, y_pred, target_names=['ESI 1', 'ESI 2', 'ESI 3', 'ESI 4', 'ESI 5']))