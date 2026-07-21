"""
StressKey - User Calibration Module
Establishes a personal typing baseline so the model judges
your stress relative to YOU, not the average dataset user.

How it works:
  1. User types a neutral passage for ~40 seconds (relaxed state)
  2. We record mean & std of Dwell Time and Flight Time
  3. Save to calibration.json
  4. EmotionPredictor applies Z-score transform before every prediction:
       adjusted = (current - your_baseline_mean) / your_baseline_std
     This converts absolute ms values into personal deviations.
"""

import time
import threading
import tkinter as tk
from tkinter import ttk
from collections import deque
import numpy as np

from calibration_core import CalibrationData, CALIBRATION_FILE, CALIBRATION_TEXT



# ── Calibration wizard GUI ────────────────────────────────────────────────────

# Colours (match main app)
BG       = "#1A1A2E"
BG_CARD  = "#16213E"
BG_CARD2 = "#0F3460"
WHITE    = "#E0E0E0"
DIM      = "#8892A4"
GREEN    = "#6BCB77"
ACCENT   = "#E94560"
YELLOW   = "#FFD93D"


class CalibrationWizard:
    """
    A modal Tk window that guides the user through the 40-second
    baseline capture session.
    """

    DURATION_SECS = 40

    def __init__(self, parent: tk.Tk, on_complete):
        """
        parent      — the main Tk root window
        on_complete — callback(CalibrationData) called after save
        """
        self._parent      = parent
        self._on_complete = on_complete
        self._calib_data  = CalibrationData()

        # Keystroke capture (mirrors KeyboardMonitor logic)
        self._lock          = threading.Lock()
        self._key_down_time = {}
        self._last_release  = None
        self._dwell_buf     = deque()
        self._flight_buf    = deque()
        self._listener      = None

        self._running    = False
        self._start_time = None
        self._ks_count   = 0

        self._build_window()

    # ── Window ────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.win = tk.Toplevel(self._parent)
        self.win.title("StressKey — First-Time Calibration")
        self.win.geometry("640x520")
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.grab_set()   # modal

        # Centre over parent
        self.win.update_idletasks()
        px = self._parent.winfo_x() + (self._parent.winfo_width()  - 640) // 2
        py = self._parent.winfo_y() + (self._parent.winfo_height() - 520) // 2
        self.win.geometry(f"640x520+{px}+{py}")

        self._build_intro_screen()

    def _clear_win(self):
        for w in self.win.winfo_children():
            w.destroy()

    # ── Screen 1: Introduction ────────────────────────────────────────────────

    def _build_intro_screen(self):
        self._clear_win()

        tk.Label(self.win, text="🎹", font=("Segoe UI", 40),
                 bg=BG).pack(pady=(30, 4))
        tk.Label(self.win, text="Personal Calibration",
                 font=("Segoe UI", 20, "bold"), bg=BG, fg=WHITE).pack()
        tk.Label(self.win,
                 text="This takes about 40 seconds.\nHelps StressKey learn YOUR normal typing rhythm.",
                 font=("Segoe UI", 11), bg=BG, fg=DIM,
                 justify="center").pack(pady=(8, 20))

        # Steps
        steps_frame = tk.Frame(self.win, bg=BG_CARD, padx=24, pady=16)
        steps_frame.pack(fill="x", padx=40)

        steps = [
            ("1", "Sit comfortably — you should feel calm and relaxed"),
            ("2", "Type the passage shown on the next screen"),
            ("3", "Type naturally — don't try to go fast or slow"),
            ("4", "StressKey records only timing, never what you type"),
        ]
        for num, txt in steps:
            row = tk.Frame(steps_frame, bg=BG_CARD)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=num, font=("Segoe UI", 12, "bold"),
                     bg=BG_CARD2, fg=WHITE, width=2,
                     padx=6, pady=2).pack(side="left")
            tk.Label(row, text=txt, font=("Segoe UI", 10),
                     bg=BG_CARD, fg=WHITE).pack(side="left", padx=10)

        tk.Button(self.win, text="Start Calibration →",
                  command=self._build_typing_screen,
                  bg=GREEN, fg=BG, font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10,
                  cursor="hand2").pack(pady=28)

        tk.Button(self.win, text="Skip for now",
                  command=self._skip,
                  bg=BG, fg=DIM, font=("Segoe UI", 9),
                  relief="flat").pack()

    # ── Screen 2: Typing ──────────────────────────────────────────────────────

    def _build_typing_screen(self):
        self._clear_win()

        # Header
        hdr = tk.Frame(self.win, bg=BG, pady=12)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="Type the passage below — at your normal pace",
                 font=("Segoe UI", 12, "bold"), bg=BG, fg=WHITE).pack()

        # Passage display
        passage_frame = tk.Frame(self.win, bg=BG_CARD2, padx=16, pady=12)
        passage_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(passage_frame, text=CALIBRATION_TEXT,
                 font=("Segoe UI", 10), bg=BG_CARD2, fg=WHITE,
                 wraplength=560, justify="left").pack()

        # Typing area
        tk.Label(self.win, text="Type here  ↓",
                 font=("Segoe UI", 9), bg=BG, fg=DIM).pack()

        self._text_box = tk.Text(self.win, height=4,
                                 font=("Segoe UI", 11),
                                 bg=BG_CARD, fg=WHITE,
                                 insertbackground=WHITE,
                                 relief="flat", padx=10, pady=8,
                                 wrap="word")
        self._text_box.pack(fill="x", padx=20, pady=(2, 12))
        self._text_box.focus_set()

        # Progress bar
        prog_frame = tk.Frame(self.win, bg=BG, padx=20)
        prog_frame.pack(fill="x")

        self._lbl_status = tk.Label(prog_frame,
                                    text="⏳  Press any key to begin…",
                                    font=("Segoe UI", 10), bg=BG, fg=YELLOW)
        self._lbl_status.pack(anchor="w")

        self._lbl_ks = tk.Label(prog_frame, text="Keystrokes: 0",
                                font=("Segoe UI", 9), bg=BG, fg=DIM)
        self._lbl_ks.pack(anchor="w")

        self._progress = ttk.Progressbar(prog_frame, length=560,
                                         maximum=self.DURATION_SECS,
                                         mode="determinate")
        self._progress.pack(fill="x", pady=6)

        self._lbl_time = tk.Label(prog_frame, text="0 / 40 seconds",
                                  font=("Segoe UI", 9), bg=BG, fg=DIM)
        self._lbl_time.pack(anchor="e")

        # Start listening
        self._start_listener()
        self._text_box.bind("<Key>", self._on_first_key)

    def _on_first_key(self, event=None):
        """Called once on first keystroke — starts the timer."""
        if not self._running:
            self._running    = True
            self._start_time = time.time()
            self._lbl_status.config(text="🟢  Recording… keep typing!",
                                    fg=GREEN)
            self._tick()

    def _tick(self):
        """Update progress bar every 500ms."""
        if not self._running:
            return
        elapsed = time.time() - self._start_time
        self._progress["value"] = min(elapsed, self.DURATION_SECS)
        self._lbl_time.config(text=f"{int(elapsed)} / {self.DURATION_SECS} seconds")
        self._lbl_ks.config(text=f"Keystrokes recorded: {self._ks_count}")

        if elapsed >= self.DURATION_SECS:
            self._running = False
            self._stop_listener()
            self._finish_calibration()
        else:
            self.win.after(500, self._tick)

    # ── Screen 3: Results ─────────────────────────────────────────────────────

    def _finish_calibration(self):
        with self._lock:
            dwells  = [x for x in self._dwell_buf  if 10 < x < 500]
            flights = [x for x in self._flight_buf if  0 < x < 2000]

        result = self._calib_data.compute_from_samples(dwells, flights)
        if result is None:
            self._build_error_screen(
                f"Not enough data ({len(dwells)} dwell, {len(flights)} flight samples).\n"
                "Please try again and type more during the 40 seconds."
            )
            return

        means, stds = result
        self._calib_data.save(means, stds)
        self._build_result_screen(means, len(dwells), len(flights))

    def _build_result_screen(self, means: dict, n_dwell: int, n_flight: int):
        self._clear_win()

        tk.Label(self.win, text="✅", font=("Segoe UI", 40),
                 bg=BG).pack(pady=(24, 4))
        tk.Label(self.win, text="Calibration Complete!",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=GREEN).pack()
        tk.Label(self.win,
                 text="StressKey now knows YOUR normal typing rhythm.",
                 font=("Segoe UI", 10), bg=BG, fg=DIM).pack(pady=(4, 16))

        # Stats card
        card = tk.Frame(self.win, bg=BG_CARD, padx=24, pady=16)
        card.pack(fill="x", padx=40)

        tk.Label(card, text="Your personal baseline",
                 font=("Segoe UI", 10, "bold"), bg=BG_CARD,
                 fg=DIM).pack(anchor="w", pady=(0, 8))

        stats = [
            ("Avg dwell time (key held)",
             f"{means['D1U1_mean']:.1f} ms",
             "How long you hold each key"),
            ("Avg flight time (between keys)",
             f"{means['D1D2_mean']:.1f} ms",
             "Gap between your keystrokes"),
            ("Typing speed proxy",
             f"{means['Speed_Proxy']:.2f}",
             "Higher = faster typist"),
            ("Total keystrokes captured",
             str(n_dwell + n_flight),
             "Used to compute the baseline"),
        ]

        for label, value, hint in stats:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label, font=("Segoe UI", 10),
                     bg=BG_CARD, fg=WHITE).pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=GREEN).pack(side="right")

        tk.Label(self.win,
                 text="You can re-calibrate anytime from the main window.",
                 font=("Segoe UI", 9), bg=BG, fg=DIM).pack(pady=12)

        tk.Button(self.win, text="Start Using StressKey →",
                  command=self._complete,
                  bg=GREEN, fg=BG, font=("Segoe UI", 12, "bold"),
                  relief="flat", padx=20, pady=10,
                  cursor="hand2").pack()

    def _build_error_screen(self, msg: str):
        self._clear_win()
        tk.Label(self.win, text="⚠️", font=("Segoe UI", 36),
                 bg=BG).pack(pady=(30, 8))
        tk.Label(self.win, text="Not enough data",
                 font=("Segoe UI", 16, "bold"), bg=BG, fg=YELLOW).pack()
        tk.Label(self.win, text=msg, font=("Segoe UI", 10),
                 bg=BG, fg=DIM, wraplength=480, justify="center").pack(pady=12)

        tk.Button(self.win, text="Try Again",
                  command=self._build_typing_screen,
                  bg=ACCENT, fg=WHITE, font=("Segoe UI", 11, "bold"),
                  relief="flat", padx=16, pady=8,
                  cursor="hand2").pack(pady=8)
        tk.Button(self.win, text="Skip for now",
                  command=self._skip,
                  bg=BG, fg=DIM, relief="flat").pack()

    # ── Keyboard listener (captures timing only) ─────────────────────────────

    def _start_listener(self):
        from pynput import keyboard
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False
        )
        self._listener.start()

    def _stop_listener(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key):
        now = time.time() * 1000
        kid = str(key)
        with self._lock:
            self._key_down_time[kid] = now
            if self._last_release is not None and self._running:
                ft = now - self._last_release
                if 0 < ft < 3000:
                    self._flight_buf.append(ft)

        # First key starts timer
        if not self._running:
            self.win.after(0, self._on_first_key)

    def _on_release(self, key):
        now = time.time() * 1000
        kid = str(key)
        with self._lock:
            press_time = self._key_down_time.pop(kid, None)
            if press_time is not None and self._running:
                dwell = now - press_time
                if 10 < dwell < 500:
                    self._dwell_buf.append(dwell)
                    self._ks_count += 1
            self._last_release = now

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _skip(self):
        self._stop_listener()
        self.win.destroy()
        # Return uncalibrated data so app still launches
        self._on_complete(self._calib_data)

    def _complete(self):
        self._stop_listener()
        self.win.destroy()
        self._on_complete(self._calib_data)


# ── Convenience launcher ──────────────────────────────────────────────────────

def launch_calibration_if_needed(root: tk.Tk, on_complete):
    """
    Open the calibration wizard only if no calibration file exists yet.
    Otherwise load existing data and call on_complete immediately.
    """
    data = CalibrationData()
    if data.is_calibrated:
        on_complete(data)
    else:
        CalibrationWizard(root, on_complete)


def force_recalibrate(root: tk.Tk, on_complete):
    """Always open the calibration wizard (for re-calibration button)."""
    CalibrationWizard(root, on_complete)