"""
StressKey - Step 1: Train the Emotion Classification Model
Run this file ONCE to generate stress_model.pkl
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os

print("=" * 50)
print("  StressKey - Model Training")
print("=" * 50)

# ── 1. Load dataset ──────────────────────────────
CSV_PATH = "Master_Dataset_Augmented_5k.csv"
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"❌ Cannot find '{CSV_PATH}'.\n"
        "Please place the CSV file in the same folder as this script."
    )

df = pd.read_csv(CSV_PATH)
print(f"✅ Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

# ── 2. Filter Free Text rows only ────────────────
df = df[df['textIndex'] == 'FR'].copy()
print(f"✅ After filtering Free Text rows: {df.shape[0]} rows")

# ── 3. Drop columns not useful for prediction ────
DROP_COLS = ['User ID', 'textIndex', 'TotTime', 'status',
             'degree', 'country', 'pcTimeAverage']
df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)

# ── 4. Handle missing values ─────────────────────
numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
print(f"✅ Missing values handled")

# ── 5. Outlier capping (IQR) on key timing cols ──
timing_cols = ['D1U1_mean', 'D1U1_std', 'D1D2_mean',
               'D1D2_std', 'U1D2_mean', 'U1D2_std']
for col in timing_cols:
    if col in df.columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df[col] = np.where(df[col] > upper, upper,
                  np.where(df[col] < lower, lower, df[col]))
print(f"✅ Outliers capped using IQR method")

# ── 6. Encode categorical features ───────────────
cat_cols = ['typeWith', 'typistType', 'gender', 'ageRange']
label_encoders = {}
for col in cat_cols:
    if col in df.columns:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
print(f"✅ Categorical features encoded")

# ── 7. Encode target label ────────────────────────
# S=Stressed, A=Angry, N=Neutral, H=Happy, C=Calm
target_le = LabelEncoder()
df['emotionIndex'] = target_le.fit_transform(df['emotionIndex'])
print(f"✅ Emotion classes: {dict(zip(target_le.classes_, target_le.transform(target_le.classes_)))}")

# ── 8. Feature / Target split ────────────────────
FEATURE_COLS = [c for c in df.columns if c != 'emotionIndex']
X = df[FEATURE_COLS]
y = df['emotionIndex']

# ── 9. Standardize numeric features ──────────────
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(f"✅ Features standardized. Total features: {X.shape[1]}")

# ── 10. Train / Test split ────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

# ── 11. Train Random Forest ───────────────────────
print("\n🔄 Training Random Forest... (may take ~10 seconds)")
clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
clf.fit(X_train, y_train)

# ── 12. Evaluate ──────────────────────────────────
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"\n✅ Test Accuracy: {acc * 100:.2f}%")
print("\nClassification Report:")
print(classification_report(y_test, y_pred,
      target_names=target_le.classes_))

# ── 13. Save model + supporting objects ──────────
model_data = {
    "model": clf,
    "scaler": scaler,
    "label_encoders": label_encoders,
    "target_encoder": target_le,
    "feature_cols": FEATURE_COLS,
}
with open("stress_model.pkl", "wb") as f:
    pickle.dump(model_data, f)

print("\n✅ Model saved to: stress_model.pkl")
print("=" * 50)
print("  Training complete! Now run: python gui_app.py")
print("=" * 50)
