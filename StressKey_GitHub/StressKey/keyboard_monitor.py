"""
StressKey - Keyboard Monitor Module
Captures Dwell Time (D1U1) and Flight Time (D1D2) in real-time
using pynput. No keystrokes are stored - only timing values.
"""

import time
import threading
from collections import deque


class KeyboardMonitor:
    """
    Non-intrusive keyboard timing monitor.
    Tracks only WHEN keys are pressed/released, never WHAT was typed.
    """

    WINDOW_SIZE = 60        # Number of keystrokes to average over
    MIN_SAMPLES  = 30       # Minimum samples before making a prediction

    def __init__(self):
        self._lock           = threading.Lock()
        self._key_down_time  = {}          # key → timestamp of press
        self._dwell_times    = deque(maxlen=self.WINDOW_SIZE)
        self._flight_times   = deque(maxlen=self.WINDOW_SIZE)
        self._last_release   = None        # timestamp of last key release
        self._listener       = None
        self._running        = False
        self._keystroke_count = 0

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self):
        """Start listening in a background thread."""
        from pynput import keyboard
        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False          # Never block keystrokes
        )
        self._listener.start()

    def stop(self):
        """Stop the listener."""
        self._running = False
        if self._listener:
            self._listener.stop()

    def get_features(self) -> dict | None:
        """
        Returns a dict of averaged timing features, or None if not enough
        data has been collected yet.
        """
        with self._lock:
            if (len(self._dwell_times) < self.MIN_SAMPLES or
                    len(self._flight_times) < self.MIN_SAMPLES):
                return None

            dwell  = list(self._dwell_times)
            flight = list(self._flight_times)

        d_arr = [x for x in dwell  if 10 < x < 500]   # sane range ms
        f_arr = [x for x in flight if  0 < x < 2000]

        if len(d_arr) < 4 or len(f_arr) < 4:
            return None

        import numpy as np
        return {
            "D1U1_mean": float(np.mean(d_arr)),
            "D1U1_std":  float(np.std(d_arr)),
            "D1D2_mean": float(np.mean(f_arr)),
            "D1D2_std":  float(np.std(f_arr)),
            "U1D2_mean": float(np.mean(f_arr)),   # approximate
            "U1D2_std":  float(np.std(f_arr)),
            "Speed_Proxy": float(len(d_arr) / max(1, sum(d_arr) / 1000)),
            "delFreq":   0,
            "leftFreq":  0,
        }

    @property
    def keystroke_count(self) -> int:
        return self._keystroke_count

    # ── Internal callbacks ────────────────────────────────────────────────────

    def _on_press(self, key):
        if not self._running:
            return
        now = time.time() * 1000   # ms
        key_id = self._key_id(key)
        with self._lock:
            self._key_down_time[key_id] = now
            # Flight time = gap from last release to this press
            if self._last_release is not None:
                ft = now - self._last_release
                if 0 < ft < 3000:           # ignore very long pauses
                    self._flight_times.append(ft)

    def _on_release(self, key):
        if not self._running:
            return
        now = time.time() * 1000
        key_id = self._key_id(key)
        with self._lock:
            press_time = self._key_down_time.pop(key_id, None)
            if press_time is not None:
                dwell = now - press_time
                if 10 < dwell < 500:
                    self._dwell_times.append(dwell)
                    self._keystroke_count += 1
            self._last_release = now

    @staticmethod
    def _key_id(key) -> str:
        try:
            return key.char or str(key)
        except AttributeError:
            return str(key)
