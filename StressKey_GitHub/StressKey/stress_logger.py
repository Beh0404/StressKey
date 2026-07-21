"""
StressKey - Stress Logger Module
=================================
Persistent storage layer for emotion detection history.

Every confirmed emotion prediction is appended to a JSON Lines file
(stress_log.jsonl), one JSON object per line. This survives application
restarts and provides the data source for the weekly report generator.

Why JSONL instead of a database:
  - Append-only writes are atomic per line (no corruption risk on crash)
  - Human-readable and easy to inspect during development
  - No database server or schema migration overhead for a single-user app
  - Trivial to stream-read line by line for large histories

Each log entry records:
  ts          - ISO 8601 timestamp of the detection
  code        - emotion code (S/A/N/H/C)
  confidence  - model confidence 0..1
  dwell_ms    - mean dwell time at detection
  flight_ms   - mean flight time at detection
  music_title - recommended track (if any)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


LOG_FILE = "stress_log.jsonl"


class StressLogger:
    """Append-only logger for emotion detection events."""

    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = Path(log_path)
        # Ensure the file exists so downstream readers never fail
        if not self.log_path.exists():
            self.log_path.touch()

    # ── Writing ───────────────────────────────────────────────────────────────

    def log(self, code: str, confidence: float,
            dwell_ms: float | None = None,
            flight_ms: float | None = None,
            music_title: str | None = None):
        """Append a single detection event to the log file."""
        entry = {
            "ts":          datetime.now().isoformat(),
            "code":        code,
            "confidence":  round(float(confidence), 4),
            "dwell_ms":    round(float(dwell_ms), 1)  if dwell_ms  is not None else None,
            "flight_ms":   round(float(flight_ms), 1) if flight_ms is not None else None,
            "music_title": music_title,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠️  StressLogger write failed: {e}")

    # ── Reading ───────────────────────────────────────────────────────────────

    def read_all(self) -> list[dict]:
        """Read every logged entry. Returns a list of dicts."""
        entries = []
        if not self.log_path.exists():
            return entries
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue   # skip any corrupted line
        except Exception as e:
            print(f"⚠️  StressLogger read failed: {e}")
        return entries

    def read_range(self, start: datetime, end: datetime) -> list[dict]:
        """Read entries whose timestamp falls within [start, end)."""
        result = []
        for entry in self.read_all():
            try:
                ts = datetime.fromisoformat(entry["ts"])
            except (ValueError, KeyError):
                continue
            if start <= ts < end:
                result.append(entry)
        return result

    def read_last_days(self, days: int = 7) -> list[dict]:
        """Read entries from the last N days (default 7 for weekly report)."""
        end   = datetime.now()
        start = end - timedelta(days=days)
        return self.read_range(start, end)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def entry_count(self) -> int:
        """Total number of logged entries."""
        return len(self.read_all())

    def clear(self):
        """Wipe the log file (used for testing or user reset)."""
        try:
            self.log_path.write_text("")
        except Exception as e:
            print(f"⚠️  StressLogger clear failed: {e}")


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random

    print("Running StressLogger self-test...")
    logger = StressLogger("test_stress_log.jsonl")
    logger.clear()

    # Simulate a week of detections
    codes = ["S", "A", "N", "H", "C"]
    now = datetime.now()
    for day in range(7):
        for _ in range(random.randint(5, 20)):
            logger.log(
                code=random.choice(codes),
                confidence=random.uniform(0.4, 0.95),
                dwell_ms=random.uniform(80, 140),
                flight_ms=random.uniform(250, 400),
                music_title="Test Track",
            )

    total = logger.entry_count()
    week  = len(logger.read_last_days(7))
    print(f"✅ Logged {total} entries, {week} in last 7 days")

    # Cleanup
    Path("test_stress_log.jsonl").unlink(missing_ok=True)
    print("✅ Self-test passed")
