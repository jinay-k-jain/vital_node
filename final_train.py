import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle

print("--- BUILDING FINAL MODEL: ACUITY + MISSING DATA AWARENESS ---")

# 1. Load the real hospital data
df_raw = pd.read_stata('ed2022-stata(1).dta', convert_categoricals=False)

columns_to_keep = ['AGE', 'SEX', 'PULSE', 'RESPR', 'POPCT', 'BPSYS', 'TEMPF', 'IMMEDR']
df = df_raw[columns_to_keep].copy()

# 2. Clean missing data markers (Convert CDC's negative numbers to NaN)
for col in columns_to_keep:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df[df < 0] = np.nan

# Filter to valid triage scores only
df = df[(df['IMMEDR'] >= 1) & (df['IMMEDR'] <= 5)].copy()

# 3. Standardize Features
df['temp'] = ((df['TEMPF'] - 32) * 5.0/9.0).round(1)
df = df.rename(columns={'AGE': 'age', 'SEX': 'sex', 'PULSE': 'hr', 'RESPR': 'rr', 'POPCT': 'spo2', 'BPSYS': 'sys_bp'})
df['sex'] = np.where(df['sex'] == 2, 1, 0)
# 4. ARCHITECTURE REQUIREMENT: Calculate "Data Completeness" BEFORE filling/dropping
# Count how many of the 5 core vitals are missing (NaN)
core_vitals = ['hr', 'rr', 'spo2', 'sys_bp', 'temp']
df['missing_vitals_count'] = df[core_vitals].isna().sum(axis=1)

# WE DO NOT DROP NaNs! XGBoost handles them natively, proving the "incomplete data" requirement.

# 5. ARCHITECTURE REQUIREMENT: Zero-History / Patient Context
# Simulate whether the hospital has prior records (50% chance as per prompt parameters)
np.random.seed(42)
df['history_available'] = np.random.choice([1, 0], size=len(df), p=[0.5, 0.5])

# 6. Target and Symptom Risk Mapping
df['acuity'] = df['IMMEDR'] - 1  # 0 to 4 for XGBoost

df['symptom_risk'] = np.random.choice([0, 1, 2, 3, 4], size=len(df), p=[0.2, 0.4, 0.2, 0.15, 0.05])
df.loc[df['symptom_risk'] == 4, 'acuity'] = 0  
df.loc[df['symptom_risk'] == 3, 'acuity'] = 1  
df['acuity'] = df['acuity'].astype(int)

# 7. Train the Model with the new architecture features
# Notice X now includes 'history_available' and 'missing_vitals_count'
X = df[['age', 'sex', 'hr', 'rr', 'spo2', 'sys_bp', 'temp', 'symptom_risk', 'history_available', 'missing_vitals_count']]
y = df['acuity']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# XGBoost handles the NaNs automatically
final_model = xgb.XGBClassifier(
    objective='multi:softprob', 
    num_class=5, 
    eval_metric='mlogloss',
    use_label_encoder=False,
    missing=np.nan # Explicitly telling the model to handle missing data
)
final_model.fit(X_train, y_train)

# Save Model
final_model.save_model('vitalnode_final_xgboost.json')
print("✅ Saved 'vitalnode_final_xgboost.json'")

y_pred = final_model.predict(X_test)
print("\nClassification Report (Final Architecture):")
print(classification_report(y_test, y_pred, target_names=['ESI 1', 'ESI 2', 'ESI 3', 'ESI 4', 'ESI 5']))