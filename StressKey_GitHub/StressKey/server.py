"""
StressKey - Backend Server
─────────────────────────────────────────────────
Local daemon that:
  1. Listens to keyboard timing via KeyboardMonitor
  2. Runs ML emotion prediction via EmotionPredictor
  3. Gets music recommendations via MusicRecommender
  4. Streams everything to the React frontend over WebSocket

Run:  python server.py
Then open the React dev server (npm run dev) which connects to
ws://localhost:8000/ws

This file replaces gui_app.py as the runtime entry point when
using the web frontend. The tkinter app (gui_app.py) still works
standalone if you prefer the desktop version.
"""

import warnings
import os
# Suppress ALL sklearn internal warnings (feature-name mismatch, parallel
# worker config, deprecation notices). These are harmless informational
# messages but they spam the console every 3 seconds during live prediction,
# eventually freezing PyCharm's Run window. The env var approach propagates
# to child threads/processes that filterwarnings alone cannot reach.
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sklearn")
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

import asyncio
import json
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse

from keyboard_monitor import KeyboardMonitor
from emotion_predictor import EmotionPredictor
from music_recommender import MusicRecommender, EMOTION_MUSIC_MAP
from calibration_core import CalibrationData, CALIBRATION_TEXT
from stress_logger import StressLogger
from weekly_report import generate_report
from intervention_tracker import InterventionTracker, format_duration


# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="StressKey Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Shared state ───────────────────────────────────────────────────────────────

class AppState:
    MIN_KEYSTROKES      = 15
    PREDICT_INTERVAL_S  = 3.0

    def __init__(self):
        self.monitor      = KeyboardMonitor()
        self.predictor    = EmotionPredictor()
        self.recommender  = MusicRecommender()
        self.calibration  = CalibrationData()
        if self.calibration.is_calibrated:
            self.predictor.set_calibration(self.calibration)

        self.logger       = StressLogger()   # persistent history to disk
        self.tracker      = InterventionTracker()   # recovery-time state machine

        self.current_emotion = "N"
        self.confidence       = 0.0
        self.proba            = {}
        self.last_suggestion  = None
        self.session_start    = time.time()
        self.history           = []   # [{ts, code, dwell}]
        self.monitoring_active = False

        self._calibration_session = None   # in-progress calibration buffer

    def start_monitoring(self):
        if not self.monitoring_active:
            self.monitor.start()
            self.monitoring_active = True

    def stop_monitoring(self):
        if self.monitoring_active:
            self.monitor.stop()
            self.monitoring_active = False

    def run_prediction(self):
        """Returns an update dict if a new prediction was made, else None."""
        if self.monitor.keystroke_count < self.MIN_KEYSTROKES:
            return None
        features = self.monitor.get_features()
        if not features:
            return None

        code, conf, proba = self.predictor.predict(features)
        if conf <= 0.25:
            return None

        old_code = self.current_emotion
        self.current_emotion = code
        self.confidence       = conf
        self.proba            = proba

        changed = (code != old_code) or (self.last_suggestion is None)
        if changed:
            self.last_suggestion = self.recommender.recommend(code)
            entry = {
                "ts":    datetime.now().isoformat(),
                "code":  code,
                "dwell": features.get("D1U1_mean"),
            }
            self.history.append(entry)

            # Persist to disk for the weekly report
            self.logger.log(
                code=code,
                confidence=conf,
                dwell_ms=features.get("D1U1_mean"),
                flight_ms=features.get("D1D2_mean"),
                music_title=(self.last_suggestion.title
                             if self.last_suggestion else None),
            )

        # Feed the intervention tracker regardless of whether the emotion
        # "changed" per se — it needs every confirmed detection to know
        # when a stress episode starts/continues/resolves.
        tracker_event = self.tracker.on_detection(
            code=code, confidence=conf,
            music_title=(self.last_suggestion.title
                         if self.last_suggestion else None),
        ) if changed else None

        return {
            "type":       "prediction",
            "emotion":    code,
            "confidence": conf,
            "proba":      proba,
            "changed":    changed,
            "features": {
                "dwell_ms":  round(features.get("D1U1_mean", 0), 1),
                "flight_ms": round(features.get("D1D2_mean", 0), 1),
            },
            "keystrokes": self.monitor.keystroke_count,
            "music": self._suggestion_payload(),
            "recovery_event": tracker_event,
        }

    def _suggestion_payload(self):
        s = self.last_suggestion
        if not s:
            return None
        info = EMOTION_MUSIC_MAP.get(self.current_emotion, EMOTION_MUSIC_MAP["N"])
        return {
            "title":       s.title,
            "artist":      s.artist,
            "url":         s.url,
            "description": s.description,
            "emoji":       s.emoji,
            "color":       info["color"],
            "label":       info["label"],
        }

    def snapshot(self):
        """Full current state — sent when a client first connects."""
        elapsed = int(time.time() - self.session_start)
        return {
            "type":               "snapshot",
            "emotion":            self.current_emotion,
            "confidence":         self.confidence,
            "proba":              self.proba,
            "keystrokes":         self.monitor.keystroke_count,
            "session_seconds":    elapsed,
            "monitoring_active":  self.monitoring_active,
            "is_calibrated":      self.calibration.is_calibrated,
            "calibrated_at":      self.calibration.calibrated_at,
            "music":              self._suggestion_payload(),
            "history":            self.history[-30:],
        }


state = AppState()


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── Background prediction loop ────────────────────────────────────────────────

async def prediction_loop():
    while True:
        await asyncio.sleep(state.PREDICT_INTERVAL_S)
        if not state.monitoring_active:
            continue
        update = state.run_prediction()
        if update:
            await manager.broadcast(update)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(prediction_loop())
    asyncio.create_task(heartbeat_loop())


async def heartbeat_loop():
    """Send lightweight session-timer ticks every second."""
    while True:
        await asyncio.sleep(1.0)
        elapsed = int(time.time() - state.session_start)
        await manager.broadcast({
            "type": "tick",
            "session_seconds": elapsed,
            "keystrokes": state.monitor.keystroke_count,
            "monitoring_active": state.monitoring_active,
        })


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    await ws.send_json(state.snapshot())

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await handle_client_message(ws, msg)
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def handle_client_message(ws: WebSocket, msg: dict):
    action = msg.get("action")

    if action == "start_monitoring":
        state.start_monitoring()
        await manager.broadcast({"type": "status",
                                 "monitoring_active": True})

    elif action == "stop_monitoring":
        state.stop_monitoring()
        await manager.broadcast({"type": "status",
                                 "monitoring_active": False})

    elif action == "play_music":
        if state.last_suggestion:
            state.recommender.play(state.last_suggestion)
            await ws.send_json({"type": "played",
                               "url": state.last_suggestion.url})

    elif action == "refresh_music":
        state.last_suggestion = state.recommender.recommend(state.current_emotion)
        await manager.broadcast({"type": "music_update",
                                 "music": state._suggestion_payload()})

    elif action == "get_calibration_text":
        await ws.send_json({"type": "calibration_text",
                           "text": CALIBRATION_TEXT,
                           "duration_secs": 40})

    elif action == "calibration_keystroke":
        # Client streams {dwell, flight} samples while user types
        _handle_calibration_sample(msg)

    elif action == "calibration_finish":
        result = _finish_calibration()
        await ws.send_json(result)

    elif action == "skip_calibration":
        state._calibration_session = None
        await ws.send_json({"type": "calibration_skipped"})


# ── Calibration helpers (mirrors calibration.py logic) ────────────────────────

def _handle_calibration_sample(msg: dict):
    if state._calibration_session is None:
        state._calibration_session = {"dwells": [], "flights": []}
    sess = state._calibration_session
    dwell  = msg.get("dwell")
    flight = msg.get("flight")
    if dwell is not None and 10 < dwell < 500:
        sess["dwells"].append(dwell)
    if flight is not None and 0 < flight < 2000:
        sess["flights"].append(flight)


def _finish_calibration():
    sess = state._calibration_session
    if not sess:
        return {"type": "calibration_error",
               "message": "No calibration session in progress."}

    result = state.calibration.compute_from_samples(
        sess["dwells"], sess["flights"])
    if result is None:
        return {"type": "calibration_error",
               "message": "Not enough keystrokes captured. Please try again."}

    means, stds = result
    state.calibration.save(means, stds)
    state.predictor.set_calibration(state.calibration)
    n_samples = len(sess["dwells"]) + len(sess["flights"])
    state._calibration_session = None

    return {
        "type": "calibration_complete",
        "means": means,
        "calibrated_at": state.calibration.calibrated_at,
        "n_samples": n_samples,
    }


# ── REST fallback endpoints (optional, useful for debugging) ─────────────────

@app.get("/api/status")
def get_status():
    return state.snapshot()

@app.post("/api/start")
def api_start():
    state.start_monitoring()
    return {"monitoring_active": True}

@app.post("/api/stop")
def api_stop():
    state.stop_monitoring()
    return {"monitoring_active": False}


@app.get("/api/report")
def api_report(days: int = 7):
    """Generate a weekly PDF report and return it as a download."""
    path = generate_report(days=days)
    if path is None:
        return {"error": "No data available to generate a report yet. "
                         "Use the system for a while first."}
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.split("/")[-1],
    )


@app.get("/api/report/stats")
def api_report_stats(days: int = 7):
    """Return summary statistics without generating a PDF (for UI preview)."""
    from weekly_report import _compute_metrics
    entries = state.logger.read_last_days(days)
    metrics = _compute_metrics(entries)
    if metrics is None:
        return {"has_data": False}
    return {
        "has_data":       True,
        "total":          metrics["total"],
        "dominant":       metrics["dominant"],
        "avg_conf":       round(metrics["avg_conf"], 1),
        "stress_events":  metrics["stress_events"],
        "music_events":   metrics["music_events"],
        "est_minutes":    round(metrics["est_minutes"]),
        "peak_hour":      metrics["peak_hour"],
    }


@app.get("/api/recovery/stats")
def api_recovery_stats(days: int = 7):
    """Return intervention recovery-time statistics."""
    stats = state.tracker.get_stats(days=days)
    active_duration = state.tracker.get_active_episode_duration()
    stats["active_episode_seconds"] = active_duration
    return stats


if __name__ == "__main__":
    import uvicorn
    import logging

    # Suppress access-log spam from high-frequency polling endpoints
    # (the web dashboard polls these every few seconds). Other requests
    # still log normally, so genuine activity remains visible.
    class _EndpointFilter(logging.Filter):
        SILENCED = ("/api/recovery/stats", "/api/status")
        def filter(self, record: logging.LogRecord) -> bool:
            msg = record.getMessage()
            return not any(path in msg for path in self.SILENCED)

    logging.getLogger("uvicorn.access").addFilter(_EndpointFilter())

    print("=" * 50)
    print("  StressKey Backend Server")
    print("  WebSocket: ws://localhost:8000/ws")
    print("  REST:      http://localhost:8000/api/status")
    print("  (polling endpoint logs are suppressed to keep console clean)")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
