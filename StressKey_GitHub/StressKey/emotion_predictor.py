"""
StressKey - Emotion Predictor Module
Loads the trained model and predicts emotion from keystroke features.
"""

import warnings
import os
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from collections import deque, Counter


EMOTION_LABELS = {
    "S": "Stressed",
    "A": "Angry",
    "N": "Neutral",
    "H": "Happy",
    "C": "Calm",
}


class EmotionPredictor:
    """Wraps the trained Random Forest model for real-time prediction."""

    MODEL_PATH = "stress_model.pkl"

    # Default values for features not captured by keyboard monitor
    # (demographic / categorical) — use dataset medians
    DEFAULTS = {
        "delFreq":      0,
        "leftFreq":     0,
        "typeWith":     1,      # "2 hands" encoded
        "typistType":   2,      # "Touch Typist" encoded
        "ageRange":     1,      # "20-29" encoded
        "gender":       0,      # encoded value
        "Speed_Proxy":  3.0,
    }

    # Smoothing: vote over last N predictions before confirming emotion
    SMOOTH_WINDOW = 5   # keep last 5 predictions
    SMOOTH_NEEDED = 3   # need 3/5 same emotion to confirm change

    def __init__(self, calibration=None):
        self._model          = None
        self._scaler         = None
        self._target_enc     = None
        self._feature_cols   = None
        self._loaded         = False
        self._calibration    = calibration   # CalibrationData | None
        self._pred_history   = deque(maxlen=self.SMOOTH_WINDOW)
        self._confirmed_emotion = "N"
        self._load_model()

    def set_calibration(self, calibration):
        """Hot-swap calibration data after wizard completes."""
        self._calibration = calibration
        print(f"✅ Calibration applied to predictor "
              f"(calibrated={calibration.is_calibrated})")

    def _load_model(self):
        path = Path(self.MODEL_PATH)
        if not path.exists():
            print(f"⚠️  Model not found at '{self.MODEL_PATH}'.")
            print("   Run train_model.py first to generate the model.")
            return

        with open(path, "rb") as f:
            data = pickle.load(f)

        self._model        = data["model"]
        self._scaler       = data["scaler"]
        self._target_enc   = data["target_encoder"]
        self._feature_cols = data["feature_cols"]
        self._loaded       = True
        print(f"✅ Model loaded. Classes: {list(self._target_enc.classes_)}")

    @property
    def is_ready(self) -> bool:
        return self._loaded

    def predict(self, keystroke_features: dict) -> tuple[str, float, dict]:
        """
        Predict emotion from keystroke timing features.
        Applies personal calibration (if available) then smoothing.

        Returns:
            (emotion_code, confidence, all_probabilities)
            e.g. ("S", 0.72, {"S": 0.72, "N": 0.15, ...})
        """
        if not self._loaded:
            return "N", 0.0, {}

        # ── Step 1: Apply personal calibration Z-score transform ──────────
        features = keystroke_features
        if self._calibration and self._calibration.is_calibrated:
            features = self._calibration.apply(keystroke_features)

        # ── Step 2: Build feature row ──────────────────────────────────────
        row = {**self.DEFAULTS, **features}
        feature_row = pd.DataFrame([{
            col: row.get(col, 0) for col in self._feature_cols
        }])

        scaled = self._scaler.transform(feature_row.values)
        proba  = self._model.predict_proba(scaled)[0]
        classes = self._target_enc.classes_

        proba_dict = {cls: float(p) for cls, p in zip(classes, proba)}
        best_idx   = int(np.argmax(proba))
        raw_class  = classes[best_idx]
        confidence = float(proba[best_idx])

        # ── Step 3: Smoothing — majority vote over last N predictions ──────
        self._pred_history.append(raw_class)
        counts = Counter(self._pred_history)
        top_emotion, top_count = counts.most_common(1)[0]

        if top_count >= self.SMOOTH_NEEDED:
            self._confirmed_emotion = top_emotion

        return self._confirmed_emotion, confidence, proba_dict

    def get_label(self, code: str) -> str:
        return EMOTION_LABELS.get(code, code)
