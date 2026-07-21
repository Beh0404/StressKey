"""
StressKey - Calibration Core (no GUI dependencies)
────────────────────────────────────────────────────
Pure data logic for personal typing baseline calibration.
Used by BOTH:
  - calibration.py    (tkinter desktop wizard)
  - server.py          (FastAPI web backend)

Keeping this free of tkinter means the web backend can run
on any machine/venv without requiring a display or Tk bindings.
"""

import json
from pathlib import Path
from datetime import datetime


CALIBRATION_FILE = "calibration.json"

# Neutral passage — long enough for ~40s of typing
CALIBRATION_TEXT = (
    "The quick brown fox jumps over the lazy dog. "
    "Pack my box with five dozen liquor jugs. "
    "How vexingly quick daft zebras jump. "
    "The five boxing wizards jump quickly. "
    "Sphinx of black quartz, judge my vow. "
    "Jackdaws love my big sphinx of quartz."
)


class CalibrationData:
    """Holds the personal baseline and applies Z-score normalisation."""

    def __init__(self):
        self.is_calibrated   = False
        self.baseline_means  = {}   # feature → mean
        self.baseline_stds   = {}   # feature → std
        self.calibrated_at   = None
        self._load()

    def _load(self):
        path = Path(CALIBRATION_FILE)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.baseline_means = data.get("means", {})
            self.baseline_stds  = data.get("stds",  {})
            self.calibrated_at  = data.get("calibrated_at", "")
            self.is_calibrated  = bool(self.baseline_means)
            if self.is_calibrated:
                print(f"✅ Calibration loaded (recorded {self.calibrated_at})")
        except Exception as e:
            print(f"⚠️  Could not load calibration: {e}")

    def save(self, means: dict, stds: dict):
        self.baseline_means = means
        self.baseline_stds  = stds
        self.calibrated_at  = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.is_calibrated  = True
        data = {
            "means":          means,
            "stds":           stds,
            "calibrated_at":  self.calibrated_at,
        }
        Path(CALIBRATION_FILE).write_text(json.dumps(data, indent=2))
        print(f"✅ Calibration saved → {CALIBRATION_FILE}")

    def apply(self, features: dict) -> dict:
        """
        Z-score normalise timing features using personal baseline.
        Features without a baseline are returned unchanged.
        """
        if not self.is_calibrated:
            return features

        adjusted = dict(features)
        TIMING_KEYS = ["D1U1_mean", "D1U1_std",
                       "D1D2_mean", "D1D2_std",
                       "U1D2_mean", "U1D2_std",
                       "Speed_Proxy"]

        DATASET_MEANS = {
            "D1U1_mean": 100.0, "D1U1_std": 35.0,
            "D1D2_mean": 280.0, "D1D2_std": 200.0,
            "U1D2_mean": 280.0, "U1D2_std": 200.0,
            "Speed_Proxy": 3.0,
        }
        DATASET_STDS = {
            "D1U1_mean": 40.0,  "D1U1_std": 20.0,
            "D1D2_mean": 150.0, "D1D2_std": 120.0,
            "U1D2_mean": 150.0, "U1D2_std": 120.0,
            "Speed_Proxy": 1.5,
        }

        for key in TIMING_KEYS:
            if key not in features:
                continue
            mean = self.baseline_means.get(key)
            std  = self.baseline_stds.get(key)
            if mean is None or std is None or std < 1e-6:
                continue
            # Z-score: how many standard deviations away from YOUR calm baseline
            z  = (features[key] - mean) / std
            dm = DATASET_MEANS.get(key, mean)
            ds = DATASET_STDS.get(key, std)
            adjusted[key] = dm + z * ds   # map YOUR z-score into dataset scale

        return adjusted

    def compute_from_samples(self, dwells: list, flights: list) -> tuple[dict, dict] | None:
        """
        Given raw dwell/flight ms samples, compute (means, stds) dicts
        ready to pass to .save(). Returns None if insufficient data.
        Shared by both the tkinter wizard and the web calibration flow.
        """
        import numpy as np

        if len(dwells) < 20 or len(flights) < 20:
            return None

        dwell_arr  = np.array(dwells)
        flight_arr = np.array(flights)
        speed_proxy = len(dwells) / max(1, sum(dwells) / 1000)

        means = {
            "D1U1_mean":  float(np.mean(dwell_arr)),
            "D1U1_std":   float(np.std(dwell_arr)),
            "D1D2_mean":  float(np.mean(flight_arr)),
            "D1D2_std":   float(np.std(flight_arr)),
            "U1D2_mean":  float(np.mean(flight_arr)),
            "U1D2_std":   float(np.std(flight_arr)),
            "Speed_Proxy": float(speed_proxy),
        }
        stds = {
            "D1U1_mean":  float(max(np.std(dwell_arr),  1.0)),
            "D1U1_std":   float(max(np.std(dwell_arr),  1.0)),
            "D1D2_mean":  float(max(np.std(flight_arr), 1.0)),
            "D1D2_std":   float(max(np.std(flight_arr), 1.0)),
            "U1D2_mean":  float(max(np.std(flight_arr), 1.0)),
            "U1D2_std":   float(max(np.std(flight_arr), 1.0)),
            "Speed_Proxy": float(max(speed_proxy * 0.3,  0.1)),
        }
        return means, stds