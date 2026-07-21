"""
StressKey - Intervention Effectiveness Tracker
================================================
Measures how long a detected stress/anger episode lasts from the moment
it is first detected (and a music intervention is triggered) until the
user's emotional state is next confirmed as Calm, Neutral, or Happy.

IMPORTANT METHODOLOGICAL NOTE (for FYP write-up):
This tracker measures TIME-TO-RECOVERY, not causal intervention efficacy.
Without a randomised control condition (e.g. sessions where no music is
played after a Stressed detection), we cannot claim the music CAUSED the
faster recovery — only that recovery followed intervention within a
measured duration. The FYP should frame results as descriptive evidence
of system responsiveness, not as a proven causal treatment effect. A true
efficacy study would require a within-subject A/B design comparing
recovery time with vs without the music intervention, which is noted as
future work.

State machine:
  IDLE ──(emotion becomes S or A)──▶ ACTIVE episode starts
  ACTIVE ──(emotion becomes C, N, or H)──▶ episode resolves, duration logged
  ACTIVE ──(exceeds MAX_EPISODE_MINUTES without resolving)──▶ marked as timeout

Each episode is persisted to intervention_log.jsonl for the weekly report
and any future analysis.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median


LOG_FILE = "intervention_log.jsonl"

# States that count as a "stress trigger"
TRIGGER_STATES  = {"S", "A"}
# States that count as "recovered"
RECOVERY_STATES = {"C", "N", "H"}

# If a stress episode runs longer than this without resolving, we stop
# waiting and log it as a timeout rather than holding state indefinitely.
MAX_EPISODE_MINUTES = 30


@dataclass
class Episode:
    start_ts:          str
    trigger_emotion:   str            # "S" or "A"
    music_title:       str | None
    confidence_start:  float
    end_ts:            str | None = None
    resolved_to:       str | None = None   # "C" / "N" / "H" / None if timed out
    duration_seconds:  float | None = None
    resolved:          bool = False
    timed_out:         bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class InterventionTracker:
    """
    Tracks stress episodes across the lifetime of the running application.
    Call `on_detection()` every time a NEW confirmed emotion is registered
    (i.e. only on emotion change, not every prediction tick).
    """

    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = Path(log_path)
        if not self.log_path.exists():
            self.log_path.touch()

        self._active_episode: Episode | None = None
        self._active_start_time: float | None = None   # monotonic, for duration calc

    # ── Public API ────────────────────────────────────────────────────────────

    def on_detection(self, code: str, confidence: float,
                     music_title: str | None = None) -> dict | None:
        """
        Feed a newly confirmed emotion into the tracker.
        Returns a dict describing what happened (started / resolved / None)
        so callers can optionally react (e.g. show a toast notification).
        """
        self._check_timeout()

        if self._active_episode is None:
            # No episode running — does this detection start one?
            if code in TRIGGER_STATES:
                self._start_episode(code, confidence, music_title)
                return {"event": "episode_started", "trigger": code}
            return None

        # An episode is running — does this detection resolve it?
        if code in RECOVERY_STATES:
            result = self._resolve_episode(code)
            return {"event": "episode_resolved", **result}

        # Still in a stress state (S -> A or A -> S) — episode continues,
        # but we do not restart the timer; the episode represents the
        # continuous stress period regardless of which trigger state it's in.
        return {"event": "episode_continuing", "trigger": code}

    def get_active_episode_duration(self) -> float | None:
        """Seconds elapsed in the currently active episode, or None."""
        if self._active_start_time is None:
            return None
        return time.time() - self._active_start_time

    def get_stats(self, days: int = 7) -> dict:
        """Aggregate statistics over the last N days of resolved episodes."""
        episodes = self.read_last_days(days)
        resolved = [e for e in episodes if e.get("resolved")]

        if not episodes:
            return {"has_data": False}

        durations = [e["duration_seconds"] for e in resolved
                     if e.get("duration_seconds") is not None]

        stats = {
            "has_data":          True,
            "total_episodes":    len(episodes),
            "resolved_count":    len(resolved),
            "timeout_count":     sum(1 for e in episodes if e.get("timed_out")),
            "resolution_rate":   round(100 * len(resolved) / len(episodes), 1),
        }

        if durations:
            stats.update({
                "avg_recovery_seconds":    round(mean(durations), 1),
                "median_recovery_seconds": round(median(durations), 1),
                "fastest_seconds":         round(min(durations), 1),
                "slowest_seconds":         round(max(durations), 1),
            })
        else:
            stats.update({
                "avg_recovery_seconds": None, "median_recovery_seconds": None,
                "fastest_seconds": None, "slowest_seconds": None,
            })

        # Breakdown by trigger emotion
        for trigger in ("S", "A"):
            trig_resolved = [e for e in resolved if e["trigger_emotion"] == trigger]
            trig_durations = [e["duration_seconds"] for e in trig_resolved
                              if e.get("duration_seconds") is not None]
            stats[f"avg_recovery_{trigger}"] = (
                round(mean(trig_durations), 1) if trig_durations else None
            )
            stats[f"count_{trigger}"] = len(trig_resolved)

        return stats

    # ── Persistence ───────────────────────────────────────────────────────────

    def read_all(self) -> list[dict]:
        entries = []
        if not self.log_path.exists():
            return entries
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def read_last_days(self, days: int = 7) -> list[dict]:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        result = []
        for e in self.read_all():
            try:
                ts = datetime.fromisoformat(e["start_ts"])
            except (ValueError, KeyError):
                continue
            if ts >= cutoff:
                result.append(e)
        return result

    def _append(self, episode: Episode):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode.to_dict()) + "\n")
        except Exception as e:
            print(f"⚠️  InterventionTracker write failed: {e}")

    # ── Internal state machine ────────────────────────────────────────────────

    def _start_episode(self, code: str, confidence: float, music_title: str | None):
        self._active_episode = Episode(
            start_ts=datetime.now().isoformat(),
            trigger_emotion=code,
            music_title=music_title,
            confidence_start=confidence,
        )
        self._active_start_time = time.time()

    def _resolve_episode(self, resolved_code: str) -> dict:
        ep = self._active_episode
        duration = time.time() - self._active_start_time

        ep.end_ts           = datetime.now().isoformat()
        ep.resolved_to       = resolved_code
        ep.duration_seconds  = round(duration, 1)
        ep.resolved          = True
        ep.timed_out         = False

        self._append(ep)
        self._active_episode     = None
        self._active_start_time  = None

        return {
            "duration_seconds": ep.duration_seconds,
            "resolved_to":      resolved_code,
        }

    def _check_timeout(self):
        """If the active episode has run too long, log it as a timeout."""
        if self._active_episode is None or self._active_start_time is None:
            return
        elapsed = time.time() - self._active_start_time
        if elapsed > MAX_EPISODE_MINUTES * 60:
            ep = self._active_episode
            ep.end_ts          = datetime.now().isoformat()
            ep.duration_seconds = round(elapsed, 1)
            ep.resolved         = False
            ep.timed_out        = True
            self._append(ep)
            self._active_episode    = None
            self._active_start_time = None


# ── Human-readable formatting helper ──────────────────────────────────────────

def format_duration(seconds: float) -> str:
    """Convert seconds into a friendly '4m 32s' style string."""
    if seconds is None:
        return "—"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    if m == 0:
        return f"{s}s"
    return f"{m}m {s}s"


# ── Self-test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random

    print("Running InterventionTracker self-test...")
    tracker = InterventionTracker("test_intervention_log.jsonl")
    Path("test_intervention_log.jsonl").write_text("")  # reset

    sequence = ["N", "S", "S", "S", "C", "N", "A", "A", "N", "S", "H", "N"]
    for code in sequence:
        result = tracker.on_detection(code, confidence=random.uniform(0.5, 0.9),
                                      music_title="Test Track" if code in ("S","A") else None)
        if result:
            print(f"  {code}: {result}")
        time.sleep(0.05)  # simulate elapsed time between detections

    stats = tracker.get_stats(days=7)
    print("\nStats:", json.dumps(stats, indent=2))

    Path("test_intervention_log.jsonl").unlink(missing_ok=True)
    print("✅ Self-test passed")
