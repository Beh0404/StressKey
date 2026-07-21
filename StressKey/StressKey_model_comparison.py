"""
StressKey - Multi-Model Training & Comparison
=============================================
Chapter 4.5: Model Building
  - Technique 1: Random Forest (primary model, already in system)
  - Technique 2: Support Vector Machine (SVM)
  - Technique 3: K-Nearest Neighbours (KNN)
  - Technique 4: Extra Trees Classifier

Chapter 5.2: Model Evaluation & Comparison
  - Accuracy, Precision, Recall, F1-Score per model
  - Confusion matrix per model
  - Side-by-side comparison table
  - Saves all charts + final model

Run:  python model_comparison.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import pickle
import time
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score
)

# ── Plot style ────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#0D0D1A",
    "axes.facecolor":   "#1A1A35",
    "axes.edgecolor":   "#2E2E55",
    "text.color":       "#E0E0E0",
    "axes.labelcolor":  "#E0E0E0",
    "xtick.color":      "#9898C0",
    "ytick.color":      "#9898C0",
    "grid.color":       "#2E2E55",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "DejaVu Sans",
})

EMOTION_NAMES = {"A": "Angry", "C": "Calm", "H": "Happy", "N": "Neutral", "S": "Stressed"}
PALETTE = {"Random Forest": "#34e7b8", "SVM": "#7C6AF7",
           "KNN": "#FFD93D", "Extra Trees": "#FB923C"}

print("=" * 60)
print("  StressKey — Multi-Model Training & Comparison")
print("=" * 60)

# ── 1. Load & preprocess ─────────────────────────────────────────────────────
print("\n[1/5] Loading dataset...")
df = pd.read_csv("Master_Dataset_Augmented_5k.csv")
df = df[df["textIndex"] == "FR"].copy()
print(f"     Free-text rows: {len(df)}")

# Drop non-predictive columns
DROP = ["User ID", "textIndex", "TotTime", "status",
        "degree", "country", "pcTimeAverage"]
df.drop(columns=[c for c in DROP if c in df.columns], inplace=True)

# Missing values — mean imputation
num_cols = df.select_dtypes(include=["float64", "int64"]).columns
df[num_cols] = df[num_cols].fillna(df[num_cols].mean())

# Outlier capping (IQR) on timing features
timing_cols = ["D1U1_mean", "D1U1_std", "D1D2_mean",
               "D1D2_std", "U1D2_mean", "U1D2_std"]
for col in timing_cols:
    if col in df.columns:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        df[col] = np.clip(df[col], Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)

# Encode categoricals
cat_cols = ["typeWith", "typistType", "gender", "ageRange"]
le_map = {}
for col in cat_cols:
    if col in df.columns:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        le_map[col] = le

# Encode target
target_le = LabelEncoder()
df["emotionIndex"] = target_le.fit_transform(df["emotionIndex"])
class_names = [EMOTION_NAMES.get(c, c) for c in target_le.classes_]
print(f"     Classes: {list(zip(target_le.classes_, class_names))}")

# Features / target split & standardise
FEATURE_COLS = [c for c in df.columns if c != "emotionIndex"]
X = df[FEATURE_COLS].values
y = df["emotionIndex"].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train / test split (80/20, stratified)
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.20, random_state=42, stratify=y
)
print(f"     Train: {len(X_train)} | Test: {len(X_test)}")

# ── 2. Define models ──────────────────────────────────────────────────────────
print("\n[2/5] Defining models...")
MODELS = {
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    ),
    "SVM": SVC(
        kernel="rbf",
        C=10,
        gamma="scale",
        probability=True,
        random_state=42,
    ),
    "KNN": KNeighborsClassifier(
        n_neighbors=7,
        metric="euclidean",
        weights="distance",
    ),
    "Extra Trees": ExtraTreesClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    ),
}
print(f"     {len(MODELS)} models configured")

# ── 3. Train & evaluate each model ───────────────────────────────────────────
print("\n[3/5] Training & evaluating models...")

results = {}   # model_name → metrics dict
cms     = {}   # model_name → confusion matrix

for name, model in MODELS.items():
    print(f"\n     → {name}")
    t0 = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - t0

    y_pred = model.predict(X_test)

    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec  = recall_score(y_test, y_pred,    average="weighted", zero_division=0)
    f1   = f1_score(y_test, y_pred,        average="weighted", zero_division=0)
    cm   = confusion_matrix(y_test, y_pred)

    # 5-fold cross-validation accuracy
    cv_scores = cross_val_score(model, X_scaled, y, cv=5,
                                scoring="accuracy", n_jobs=-1)

    results[name] = {
        "Accuracy (%)":       round(acc * 100, 2),
        "Precision (%)":      round(prec * 100, 2),
        "Recall (%)":         round(rec * 100, 2),
        "F1-Score (%)":       round(f1 * 100, 2),
        "CV Mean (%)":        round(cv_scores.mean() * 100, 2),
        "CV Std (%)":         round(cv_scores.std() * 100, 2),
        "Train Time (s)":     round(train_time, 2),
    }
    cms[name] = cm

    print(f"       Accuracy  : {acc*100:.2f}%")
    print(f"       F1-Score  : {f1*100:.2f}%")
    print(f"       CV 5-fold : {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")
    print(f"       Train time: {train_time:.2f}s")

# ── 4. Summary table ──────────────────────────────────────────────────────────
print("\n[4/5] Generating results table...")
results_df = pd.DataFrame(results).T
print("\n" + results_df.to_string())

# Find best model
best_model_name = results_df["Accuracy (%)"].idxmax()
print(f"\n     ★ Best model: {best_model_name} "
      f"({results_df.loc[best_model_name, 'Accuracy (%)']:.2f}%)")

# ── 5. Visualisations ─────────────────────────────────────────────────────────
print("\n[5/5] Generating charts...")

model_names = list(results.keys())
colors = [PALETTE[n] for n in model_names]

# ── 5a. Comparison bar chart ──────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("StressKey — Model Comparison", fontsize=14,
             color="#E0E0E0", fontweight="bold")

metrics_to_plot = ["Accuracy (%)", "F1-Score (%)"]
for ax, metric in zip(axes, metrics_to_plot):
    vals = [results[n][metric] for n in model_names]
    bars = ax.bar(model_names, vals, color=colors,
                  width=0.55, edgecolor="#1A1A35", linewidth=0.5)
    ax.set_title(metric, fontsize=12, color="#E0E0E0", pad=8)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Score (%)", fontsize=10)
    ax.tick_params(axis="x", rotation=10, labelsize=9)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{val:.1f}%",
                ha="center", va="bottom", fontsize=9, color="#E0E0E0")

plt.tight_layout()
plt.savefig("model_comparison_bar.png", dpi=150, bbox_inches="tight",
            facecolor="#0D0D1A")
plt.close()
print("     ✅ Saved: model_comparison_bar.png")

# ── 5b. Confusion matrices ────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.suptitle("Confusion Matrices — All Models", fontsize=13,
             color="#E0E0E0", fontweight="bold", y=1.01)

for ax, name in zip(axes.flat, model_names):
    cm_norm = cms[name].astype("float") / cms[name].sum(axis=1, keepdims=True)
    sns.heatmap(cm_norm, annot=True, fmt=".2f", cmap="YlOrRd",
                xticklabels=class_names, yticklabels=class_names,
                ax=ax, linewidths=0.3, linecolor="#1A1A35",
                cbar_kws={"shrink": 0.8})
    color = PALETTE[name]
    ax.set_title(f"{name}  ({results[name]['Accuracy (%)']:.2f}%)",
                 fontsize=11, color=color, fontweight="bold")
    ax.set_xlabel("Predicted", fontsize=9)
    ax.set_ylabel("Actual", fontsize=9)
    ax.tick_params(labelsize=8)

plt.tight_layout()
plt.savefig("model_confusion_matrices.png", dpi=150, bbox_inches="tight",
            facecolor="#0D0D1A")
plt.close()
print("     ✅ Saved: model_confusion_matrices.png")

# ── 5c. CV score radar / grouped bar ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(model_names))
width = 0.2

metric_keys   = ["Accuracy (%)", "Precision (%)", "Recall (%)", "F1-Score (%)"]
metric_colors = ["#34e7b8", "#7C6AF7", "#FFD93D", "#FB923C"]

for i, (mk, mc) in enumerate(zip(metric_keys, metric_colors)):
    vals = [results[n][mk] for n in model_names]
    bars = ax.bar(x + i * width, vals, width, label=mk,
                  color=mc, alpha=0.85, edgecolor="#0D0D1A")

ax.set_xticks(x + width * 1.5)
ax.set_xticklabels(model_names, fontsize=10)
ax.set_ylim(0, 115)
ax.set_ylabel("Score (%)", fontsize=10)
ax.set_title("Accuracy · Precision · Recall · F1  —  All Models",
             fontsize=12, color="#E0E0E0", fontweight="bold")
ax.legend(loc="lower right", fontsize=9, framealpha=0.3)
ax.yaxis.grid(True, alpha=0.4)
ax.set_axisbelow(True)

plt.tight_layout()
plt.savefig("model_metrics_grouped.png", dpi=150, bbox_inches="tight",
            facecolor="#0D0D1A")
plt.close()
print("     ✅ Saved: model_metrics_grouped.png")

# ── 5d. Per-class F1 heatmap ─────────────────────────────────────────────────
per_class_f1 = {}
for name, model in MODELS.items():
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred,
                                   target_names=class_names,
                                   output_dict=True,
                                   zero_division=0)
    per_class_f1[name] = {cls: report[cls]["f1-score"] for cls in class_names}

heatmap_df = pd.DataFrame(per_class_f1).T * 100

fig, ax = plt.subplots(figsize=(9, 4))
sns.heatmap(heatmap_df, annot=True, fmt=".1f", cmap="RdYlGn",
            vmin=0, vmax=100, ax=ax, linewidths=0.4, linecolor="#1A1A35",
            cbar_kws={"label": "F1-Score (%)", "shrink": 0.9})
ax.set_title("Per-class F1-Score (%) by Model", fontsize=12,
             color="#E0E0E0", fontweight="bold")
ax.set_xlabel("Emotion Class", fontsize=10)
ax.set_ylabel("Model", fontsize=10)
ax.tick_params(labelsize=9)

plt.tight_layout()
plt.savefig("model_perclass_f1.png", dpi=150, bbox_inches="tight",
            facecolor="#0D0D1A")
plt.close()
print("     ✅ Saved: model_perclass_f1.png")

# ── 6. Save best model (if it's not already Random Forest) ───────────────────
print("\n" + "=" * 60)
print("  FINAL RESULTS SUMMARY")
print("=" * 60)
print(f"\n{'Model':<16} {'Accuracy':>10} {'F1-Score':>10} "
      f"{'Precision':>10} {'Recall':>10} {'CV Mean':>10}")
print("-" * 60)
for name in model_names:
    r = results[name]
    marker = " ★" if name == best_model_name else ""
    print(f"{name:<16} {r['Accuracy (%)']:>9.2f}% {r['F1-Score (%)']:>9.2f}% "
          f"{r['Precision (%)']:>9.2f}% {r['Recall (%)']:>9.2f}% "
          f"{r['CV Mean (%)']:>9.2f}%{marker}")

# Save full model package (best model)
best_model = MODELS[best_model_name]
model_package = {
    "model":          best_model,
    "model_name":     best_model_name,
    "scaler":         scaler,
    "label_encoders": le_map,
    "target_encoder": target_le,
    "feature_cols":   FEATURE_COLS,
    "results":        results,
}
with open("stress_model.pkl", "wb") as f:
    pickle.dump(model_package, f)
print(f"\n  ✅ Best model ({best_model_name}) saved to stress_model.pkl")

# Save results CSV for Chapter 5 table
results_df.to_csv("model_comparison_results.csv")
print("  ✅ Results table saved to model_comparison_results.csv")
print("\n  Charts generated:")
print("    • model_comparison_bar.png      (Accuracy & F1 bar chart)")
print("    • model_confusion_matrices.png  (4 confusion matrices)")
print("    • model_metrics_grouped.png     (grouped metrics bar chart)")
print("    • model_perclass_f1.png         (per-class F1 heatmap)")
print("\n" + "=" * 60)
print("  Done! Copy these files into your FYP report.")
print("=" * 60)
