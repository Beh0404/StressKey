"""
StressKey - Main GUI Application  (Redesigned v2)
"""

import warnings
import os
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sklearn")
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"

import tkinter as tk
from tkinter import ttk
import time
import math
from datetime import datetime
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from keyboard_monitor import KeyboardMonitor
from emotion_predictor import EmotionPredictor
from music_recommender import MusicRecommender, EMOTION_MUSIC_MAP
from calibration import CalibrationData, launch_calibration_if_needed, force_recalibrate
from stress_logger import StressLogger
from weekly_report import generate_report
from intervention_tracker import InterventionTracker, format_duration

try:
    from tray_icon import TrayIcon
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# Design tokens
# ── Questly-inspired palette ──────────────────────────────────────────────
# Near-black base (matches dashboard mockup chrome #1a1a1c)
BG      = "#0F0F11"      # outer app background
BG1     = "#15151A"      # page background
BG2     = "#1A1A1C"      # card surface (matches mockup chrome)
BG3     = "#242427"      # card inner / titlebar tone
BG4     = "#2E2E32"      # hover / active / track
BORDER  = "rgba"          # placeholder, unused — tkinter has no alpha borders
BORDER  = "#2C2C30"      # ring-1 ring-white/10 equivalent

TEXT1   = "#F5F5F0"      # primary text (warm off-white)
TEXT2   = "#9A9A92"      # text-white/60 equivalent
TEXT3   = "#5C5C58"      # text-white/35-40 equivalent

# Coral/orange accent — pulled straight from the workspace badge (#e8553f)
ACCENT  = "#E8553F"
ACCENT2 = "#E8553F"      # keep one accent family for consistency
GREEN   = "#28C840"      # macOS-style traffic-light green
YELLOW  = "#FEBC2E"      # macOS-style traffic-light amber
ORANGE  = "#FB923C"

FONT       = "Segoe UI"          # body font
FONT_DISPLAY = "Segoe UI Semibold"  # headline font (closest system match to Nimbus Sans)

EMOTIONS = {
    "S": {"color": "#F87171", "label": "Stressed", "icon": "!"},
    "A": {"color": "#FB923C", "label": "Angry",    "icon": "~"},
    "N": {"color": "#60A5FA", "label": "Neutral",  "icon": "o"},
    "H": {"color": "#FBD152", "label": "Happy",    "icon": "*"},
    "C": {"color": "#4ADE80", "label": "Calm",     "icon": "v"},
}

def _hex_to_rgb(c):
    c = c.lstrip("#")
    return int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)

def _hex_lighten(c, amount):
    r,g,b = _hex_to_rgb(c)
    r = min(255, int(r + (255-r)*amount))
    g = min(255, int(g + (255-g)*amount))
    b = min(255, int(b + (255-b)*amount))
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def _lerp_colour(a, b, t):
    ar,ag,ab_ = _hex_to_rgb(a)
    br,bg_,bb = _hex_to_rgb(b)
    return "#{:02x}{:02x}{:02x}".format(
        int(ar+(br-ar)*t), int(ag+(bg_-ag)*t), int(ab_+(bb-ab_)*t))


class RoundedFrame(tk.Frame):
    """
    A Frame with a rounded-rectangle background drawn on an
    underlying Canvas, mimicking Tailwind's rounded-2xl cards.
    Place child widgets inside .body (a transparent-feeling Frame).
    """
    def __init__(self, parent, bg=BG2, radius=16, border=BORDER,
                border_width=1, **kw):
        super().__init__(parent, bg=parent["bg"] if "bg" in parent.keys() else BG1)
        self._bg     = bg
        self._radius = radius
        self._border = border
        self._bw     = border_width

        self._canvas = tk.Canvas(self, highlightthickness=0,
                                 bg=self["bg"])
        self._canvas.pack(fill="both", expand=True)

        self.body = tk.Frame(self._canvas, bg=bg)
        self._body_id = self._canvas.create_window(
            0, 0, window=self.body, anchor="nw")

        self._canvas.bind("<Configure>", self._on_resize)
        self.body.bind("<Configure>", self._on_body_resize)

    def _on_body_resize(self, event=None):
        # Resize canvas to fit body content height
        req_h = self.body.winfo_reqheight()
        req_w = self.body.winfo_reqwidth()
        self._canvas.configure(height=req_h)
        self._redraw(self._canvas.winfo_width() or req_w, req_h)

    def _on_resize(self, event):
        self._redraw(event.width, event.height)
        self._canvas.itemconfig(self._body_id, width=event.width)

    def _redraw(self, w, h):
        if w < 4 or h < 4:
            return
        self._canvas.delete("bgshape")
        r = min(self._radius, w // 2, h // 2)
        self._round_rect(2, 2, w - 2, h - 2, r,
                         fill=self._bg, outline=self._border,
                         width=self._bw, tags="bgshape")
        self._canvas.tag_lower("bgshape")

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        points = [
            x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
            x2, y2-r,  x2, y2,  x2-r, y2,  x1+r, y2,
            x1, y2,  x1, y2-r,  x1, y1+r,  x1, y1,
        ]
        return self._canvas.create_polygon(points, smooth=True, **kw)


class EmotionRing(tk.Canvas):
    SIZE = 160
    def __init__(self, parent, **kw):
        super().__init__(parent, width=self.SIZE, height=self.SIZE,
                         bg=BG2, highlightthickness=0, **kw)
        self._emotion    = "N"
        self._confidence = 0.0
        self._target     = 0.0
        self._pulse      = 0.0
        self._anim_id    = None
        self._draw()

    def set_emotion(self, code, confidence):
        old = self._emotion
        self._emotion = code
        self._target  = confidence
        if old != code:
            self._pulse = 1.0
        self._animate()

    def _animate(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
        self._step()

    def _step(self):
        self._confidence += (self._target - self._confidence) * 0.15
        self._pulse = max(0.0, self._pulse - 0.07)
        self._draw()
        if abs(self._target - self._confidence) > 0.003 or self._pulse > 0:
            self._anim_id = self.after(30, self._step)

    def _draw(self):
        self.delete("all")
        S  = self.SIZE
        cx = cy = S // 2
        R  = S // 2 - 14
        info = EMOTIONS.get(self._emotion, EMOTIONS["N"])
        col  = info["color"]

        if self._pulse > 0.01:
            gr = R + 8 + int(self._pulse * 6)
            gc = _lerp_colour(BG2, col, self._pulse * 0.35)
            self.create_oval(cx-gr, cy-gr, cx+gr, cy+gr, outline=gc, width=2)

        self.create_oval(cx-R, cy-R, cx+R, cy+R, outline=BG4, width=8)

        if self._confidence > 0.01:
            self.create_arc(cx-R, cy-R, cx+R, cy+R,
                            start=90, extent=-(self._confidence*359.9),
                            outline=col, width=8, style="arc")

        inner = R - 16
        self.create_oval(cx-inner, cy-inner, cx+inner, cy+inner,
                         fill=BG3, outline=BORDER, width=1)

        self.create_text(cx, cy-8, text=info["label"][0],
                         font=(FONT, 26, "bold"), fill=col)
        self.create_text(cx, cy+16,
                         text=f"{int(self._confidence*100)}%",
                         font=(FONT, 11), fill=TEXT2)


class StressKeyApp:

    UPDATE_INTERVAL_MS  = 2000
    PREDICT_INTERVAL_MS = 3000
    MIN_KEYSTROKES      = 15

    def __init__(self, root):
        self.root = root
        self._setup_window()
        self._apply_theme()

        self.monitor      = KeyboardMonitor()
        self.predictor    = EmotionPredictor()
        self.recommender  = MusicRecommender()
        self.logger       = StressLogger()
        self.tracker      = InterventionTracker()
        self._calibration = None
        self._tray        = None
        self._window_visible = True
        self._current_emotion   = "N"
        self._confidence        = 0.0
        self._last_suggestion   = None
        self._prediction_active = False
        self._session_start     = time.time()
        self._emotion_history   = []
        self._fig    = None
        self._canvas = None

        self._build_ui()
        launch_calibration_if_needed(self.root, self._on_calibration_done)

    def _setup_window(self):
        self.root.title("StressKey — Emotion-Aware Music")
        self.root.geometry("1020x920")
        self.root.configure(bg=BG1)
        self.root.resizable(True, True)
        self.root.minsize(800, 720)
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth()  - 1020) // 2
        y = (self.root.winfo_screenheight() - 920)  // 2
        self.root.geometry(f"1020x920+{x}+{y}")

    def _apply_theme(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TProgressbar", troughcolor=BG3, background=ACCENT2,
                    bordercolor=BG3, lightcolor=ACCENT2, darkcolor=ACCENT2,
                    thickness=6)

    def _card(self, parent, title="", expand=True, radius=16):
        outer = RoundedFrame(parent, bg=BG2, radius=radius, border=BORDER)
        outer.pack(fill="both", expand=expand, pady=6)
        host = outer.body
        if title:
            tk.Label(host, text="  ".join(title), font=(FONT, 9, "bold"),
                     bg=BG2, fg=TEXT3).pack(anchor="w", padx=16, pady=(12,0))
        inner = tk.Frame(host, bg=BG2, padx=16, pady=12)
        inner.pack(fill="both", expand=True)
        return inner

    def _btn(self, parent, text, cmd, bg=BG4, fg=TEXT1,
             size=10, padx=14, pady=6):
        """
        Pill-style button. tk.Button can't truly render rounded-full,
        but high padding + flat relief + no border approximates the
        Tailwind 'rounded-full' pill look closely enough at this scale.
        """
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, font=(FONT, size),
                         relief="flat", padx=padx, pady=pady,
                         cursor="hand2", bd=0,
                         activebackground=_hex_lighten(bg, 0.12),
                         activeforeground=fg,
                         highlightthickness=0)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar — hero-style header zone (Questly-inspired)
        top = tk.Frame(self.root, bg=BG, height=72,
                       highlightbackground=BORDER, highlightthickness=1)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tl = tk.Frame(top, bg=BG)
        tl.pack(side="left", padx=24, pady=14)

        logo_badge = RoundedFrame(tl, bg=ACCENT2, radius=10, border=ACCENT2,
                                  border_width=0)
        logo_badge.pack(side="left")
        tk.Label(logo_badge.body, text="SK", font=(FONT, 14, "bold"),
                 bg=ACCENT2, fg=TEXT1, padx=10, pady=4).pack()

        tk.Label(tl, text="  StressKey",
                 font=(FONT_DISPLAY, 24, "bold"), bg=BG, fg=TEXT1).pack(side="left")
        tk.Label(tl, text="   Emotion-Aware Music",
                 font=(FONT, 11), bg=BG, fg=TEXT3).pack(side="left", pady=(6,0))

        tr = tk.Frame(top, bg=BG)
        tr.pack(side="right", padx=24, pady=14)
        tk.Label(tr, text="SESSION", font=(FONT, 9, "bold"),
                 bg=BG, fg=TEXT3).pack(side="left", padx=(0,8))
        self._lbl_time = tk.Label(tr, text="00:00",
                                  font=(FONT, 13, "bold"), bg=BG, fg=TEXT1)
        self._lbl_time.pack(side="left")

        # Status bar (bottom)
        sb = tk.Frame(self.root, bg=BG3, height=36)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        sbi = tk.Frame(sb, bg=BG3)
        sbi.pack(fill="both", expand=True, padx=16, pady=6)

        self._dot = tk.Canvas(sbi, width=10, height=10,
                              bg=BG3, highlightthickness=0)
        self._dot.pack(side="left", padx=(0, 8))
        self._dot.create_oval(1,1,9,9, fill=TEXT3, outline="")

        self._lbl_status = tk.Label(sbi, text="Initialising…",
                                    font=(FONT, 9), bg=BG3, fg=TEXT2)
        self._lbl_status.pack(side="left")

        self._btn(sbi, "⏹  Stop", self._stop,
                  bg="#3A1A1A", fg="#FF8888").pack(side="right", padx=4)
        self._btn(sbi, "🎯  Re-calibrate",
                  self._do_recalibrate).pack(side="right", padx=4)
        self._btn(sbi, "📄  Report",
                  self._generate_report).pack(side="right", padx=4)
        self._btn(sbi, "▼  Tray",
                  lambda: self.root.withdraw()).pack(side="right", padx=4)

        # Chart panel (above status bar)
        self._build_chart_panel()

        # Main body
        body = tk.Frame(self.root, bg=BG1)
        body.pack(fill="both", expand=True, padx=16, pady=(12,0))

        left = tk.Frame(body, bg=BG1)
        left.pack(side="left", fill="both", expand=True, padx=(0,6))
        self._build_emotion_card(left)
        self._build_stats_card(left)
        self._build_recovery_card(left)

        right = tk.Frame(body, bg=BG1)
        right.pack(side="right", fill="both", expand=True, padx=(6,0))
        self._build_music_card(right)
        self._build_history_card(right)

    def _build_emotion_card(self, parent):
        card = self._card(parent, "CURRENT EMOTION")

        self._ring = EmotionRing(card)
        self._ring.pack(pady=(4,0))

        self._lbl_emotion = tk.Label(card, text="Neutral",
                                     font=(FONT, 34, "bold"),
                                     bg=BG2, fg=EMOTIONS["N"]["color"])
        self._lbl_emotion.pack(pady=(6,0))

        self._lbl_conf_text = tk.Label(card, text="Waiting for data…",
                                       font=(FONT, 10), bg=BG2, fg=TEXT3)
        self._lbl_conf_text.pack(pady=(2,10))

        # Probability bars
        self._prob_bars   = {}
        self._prob_labels = {}
        bars = tk.Frame(card, bg=BG2)
        bars.pack(fill="x")

        for code, info in EMOTIONS.items():
            row = tk.Frame(bars, bg=BG2)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=info["label"], font=(FONT, 9),
                     bg=BG2, fg=TEXT3, width=8, anchor="w").pack(side="left")
            bg_bar = tk.Frame(row, bg=BG3, height=6)
            bg_bar.pack(side="left", fill="x", expand=True, padx=(4,8))
            bg_bar.pack_propagate(False)
            fill = tk.Frame(bg_bar, bg=info["color"], height=6)
            fill.place(x=0, y=0, relheight=1, relwidth=0)
            lbl = tk.Label(row, text="0%", font=(FONT,9),
                           bg=BG2, fg=TEXT3, width=4)
            lbl.pack(side="right")
            self._prob_bars[code]   = (bg_bar, fill)
            self._prob_labels[code] = lbl

    def _update_prob_bars(self, proba):
        for code, (_, fill) in self._prob_bars.items():
            p = proba.get(code, 0.0)
            fill.place(relwidth=p)
            self._prob_labels[code].config(text=f"{int(p*100)}%")

    def _build_stats_card(self, parent):
        card = self._card(parent, "SESSION STATS", expand=False)
        grid = tk.Frame(card, bg=BG2)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        rows = [("Keystrokes","_var_keystrokes"),
                ("Avg Dwell Time","_var_dwell"),
                ("Avg Flight Time","_var_flight"),
                ("Session Duration","_var_duration")]
        for i,(label,attr) in enumerate(rows):
            tk.Label(grid, text=label, font=(FONT,10),
                     bg=BG2, fg=TEXT2).grid(row=i,column=0,sticky="w",pady=5)
            var = tk.StringVar(value="—")
            tk.Label(grid, textvariable=var, font=(FONT,10,"bold"),
                     bg=BG2, fg=ACCENT2).grid(row=i,column=1,sticky="e",pady=5)
            setattr(self, attr, var)

    def _build_recovery_card(self, parent):
        card = self._card(parent, "RECOVERY INSIGHTS", expand=False)

        self._lbl_recovery_hint = tk.Label(
            card, text="Tracking how quickly you return to calm after stress…",
            font=(FONT, 9), bg=BG2, fg=TEXT3, wraplength=280, justify="left")
        self._lbl_recovery_hint.pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(card, bg=BG2)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        rows = [("Avg Recovery Time", "_var_avg_recovery"),
                ("Fastest Recovery",  "_var_fastest_recovery"),
                ("Episodes Resolved","_var_resolved_count"),
                ("Resolution Rate",  "_var_resolution_rate")]
        for i, (label, attr) in enumerate(rows):
            tk.Label(grid, text=label, font=(FONT, 10),
                     bg=BG2, fg=TEXT2).grid(row=i, column=0, sticky="w", pady=5)
            var = tk.StringVar(value="—")
            tk.Label(grid, textvariable=var, font=(FONT, 10, "bold"),
                     bg=BG2, fg=GREEN).grid(row=i, column=1, sticky="e", pady=5)
            setattr(self, attr, var)

        note = tk.Label(
            card,
            text="Note: measures time-to-recovery after detection, not a "
                 "proven causal effect of the music itself.",
            font=(FONT, 8), bg=BG2, fg=TEXT3, wraplength=280,
            justify="left")
        note.pack(anchor="w", pady=(8, 0))

    def _update_recovery_card(self):
        stats = self.tracker.get_stats(days=7)
        if not stats.get("has_data"):
            self._lbl_recovery_hint.config(
                text="No stress episodes recorded yet this week.")
            return

        self._lbl_recovery_hint.config(
            text=f"{stats['total_episodes']} stress episode(s) this week.")
        self._var_avg_recovery.set(format_duration(stats.get("avg_recovery_seconds")))
        self._var_fastest_recovery.set(format_duration(stats.get("fastest_seconds")))
        self._var_resolved_count.set(
            f"{stats['resolved_count']} / {stats['total_episodes']}")
        self._var_resolution_rate.set(f"{stats['resolution_rate']:.0f}%")

    def _build_music_card(self, parent):
        card = self._card(parent, "MUSIC RECOMMENDATION")

        art_row = tk.Frame(card, bg=BG2)
        art_row.pack(fill="x", pady=(0,10))

        self._art = tk.Canvas(art_row, width=56, height=56,
                              bg=BG3, highlightthickness=0)
        self._art.pack(side="left")
        self._draw_art("N")

        col = tk.Frame(art_row, bg=BG2)
        col.pack(side="left", fill="both", expand=True, padx=(12,0))

        self._lbl_song_desc = tk.Label(col, text="Waiting for detection…",
                                       font=(FONT,9), bg=BG2, fg=TEXT3, anchor="w")
        self._lbl_song_desc.pack(fill="x")
        self._lbl_song_title = tk.Label(col, text="—",
                                        font=(FONT,15,"bold"),
                                        bg=BG2, fg=TEXT1, anchor="w", wraplength=230)
        self._lbl_song_title.pack(fill="x", pady=(2,0))
        self._lbl_song_artist = tk.Label(col, text="",
                                         font=(FONT,10), bg=BG2, fg=TEXT2, anchor="w")
        self._lbl_song_artist.pack(fill="x")

        btns = tk.Frame(card, bg=BG2)
        btns.pack(fill="x", pady=(6,0))

        self._btn_play = self._btn(btns, "▶   Open in YouTube Music",
                                   self._play_music, bg=ACCENT,
                                   fg=TEXT1, size=11, padx=16, pady=9)
        self._btn_play.config(state="disabled", disabledforeground="#996070")
        self._btn_play.pack(side="left", fill="x", expand=True)
        self._btn(btns, "↻", self._refresh_recommendation,
                  padx=12, pady=9).pack(side="right", padx=(6,0))

    def _draw_art(self, code):
        self._art.delete("all")
        col  = EMOTIONS.get(code, EMOTIONS["N"])["color"]
        lbl  = EMOTIONS.get(code, EMOTIONS["N"])["label"][0]
        self._art.create_rectangle(0,0,56,56, fill=BG3, outline="")
        self._art.create_rectangle(0,0,4,56,  fill=col, outline="")
        self._art.create_text(28,28, text=lbl,
                              font=(FONT,24,"bold"), fill=col)

    def _build_history_card(self, parent):
        card = self._card(parent, "RECENT DETECTIONS")
        self._history_frame = tk.Frame(card, bg=BG2)
        self._history_frame.pack(fill="both", expand=True)
        tk.Label(self._history_frame, text="No detections yet",
                 font=(FONT,10), bg=BG2, fg=TEXT3).pack(pady=8)

    def _build_chart_panel(self):
        outer = RoundedFrame(self.root, bg=BG2, radius=16, border=BORDER)
        outer.pack(fill="x", side="bottom", padx=16, pady=(0,4))
        host = outer.body

        tabs_frame = tk.Frame(host, bg=BG2)
        tabs_frame.pack(fill="x")

        self._chart_tab  = tk.StringVar(value="timeline")
        self._tab_btns   = {}

        for label, key in [("📈  Timeline","timeline"),
                            ("🥧  Distribution","pie"),
                            ("⌨️  Typing Speed","dwell")]:
            b = tk.Button(tabs_frame, text=label,
                          command=lambda k=key: self._switch_tab(k),
                          bg=BG2, fg=TEXT3, font=(FONT,10),
                          relief="flat", padx=16, pady=10, cursor="hand2",
                          bd=0, highlightthickness=0,
                          activebackground=BG3, activeforeground=TEXT1)
            b.pack(side="left")
            self._tab_btns[key] = b

        self._chart_frame = tk.Frame(host, bg=BG2, height=200)
        self._chart_frame.pack(fill="both", expand=True, padx=4, pady=(0,8))
        self._chart_frame.pack_propagate(False)
        self._switch_tab("timeline")

    def _switch_tab(self, key):
        self._chart_tab.set(key)
        for k, b in self._tab_btns.items():
            if k == key:
                b.config(bg=BG3, fg=ACCENT, font=(FONT,10,"bold"))
            else:
                b.config(bg=BG2, fg=TEXT3, font=(FONT,10))
        self._rebuild_chart()

    # ── Monitoring ────────────────────────────────────────────────────────────

    def _on_calibration_done(self, calib):
        self._calibration = calib
        self.predictor.set_calibration(calib)
        if calib.is_calibrated:
            self._setstatus(f"Calibrated ({calib.calibrated_at})", GREEN, "green")
        else:
            self._setstatus("No calibration — using general model", YELLOW, "yellow")
        self.root.after(600, self._start_monitoring)

    def _start_monitoring(self):
        if not self.predictor.is_ready:
            self._setstatus("Model not found — run train_model.py first", ORANGE, "orange")
            return
        self.monitor.start()
        self._prediction_active = True
        self._schedule_predict()
        self._schedule_ui_update()
        self._setstatus("Monitoring active — type anywhere", GREEN, "green")

    def _setstatus(self, text, colour, dot):
        dc = {"green": GREEN, "yellow": YELLOW, "orange": ORANGE,
              "red": ACCENT, "gray": TEXT3}.get(dot, TEXT3)
        self._lbl_status.config(text=text, fg=colour)
        self._dot.delete("all")
        self._dot.create_oval(1,1,9,9, fill=dc, outline="")

    def _schedule_predict(self):
        if self._prediction_active:
            self._run_prediction()
            self.root.after(self.PREDICT_INTERVAL_MS, self._schedule_predict)

    def _schedule_ui_update(self):
        if self._prediction_active:
            self._update_ui()
            self.root.after(self.UPDATE_INTERVAL_MS, self._schedule_ui_update)

    def _run_prediction(self):
        if self.monitor.keystroke_count < self.MIN_KEYSTROKES:
            return
        features = self.monitor.get_features()
        if not features:
            return
        code, conf, proba = self.predictor.predict(features)
        if conf > 0.25:
            old = self._current_emotion
            self._current_emotion = code
            self._confidence      = conf
            self.root.after(0, lambda p=proba: self._update_prob_bars(p))
            if code != old or self._last_suggestion is None:
                self._last_suggestion = self.recommender.recommend(code)
                dwell = features.get("D1U1_mean")
                self._emotion_history.append((datetime.now(), code, dwell))
                self.logger.log(
                    code=code, confidence=conf,
                    dwell_ms=dwell, flight_ms=features.get("D1D2_mean"),
                    music_title=(self._last_suggestion.title
                                 if self._last_suggestion else None))
                tracker_event = self.tracker.on_detection(
                    code=code, confidence=conf,
                    music_title=(self._last_suggestion.title
                                 if self._last_suggestion else None))
                if tracker_event and tracker_event.get("event") == "episode_resolved":
                    dur = format_duration(tracker_event["duration_seconds"])
                    self.root.after(0, lambda d=dur: self._setstatus(
                        f"Recovered in {d} — great job!", GREEN, "green"))
                self.root.after(0, self._refresh_music_ui)
                self.root.after(100, self._rebuild_chart)
                if self._tray:
                    self._tray.update_emotion(
                        code, self._last_suggestion.title
                        if self._last_suggestion else "—")

    def _update_ui(self):
        elapsed = int(time.time() - self._session_start)
        m, s = divmod(elapsed, 60)
        self._lbl_time.config(text=f"{m:02d}:{s:02d}")

        info = EMOTIONS.get(self._current_emotion, EMOTIONS["N"])
        self._ring.set_emotion(self._current_emotion, self._confidence)
        self._lbl_emotion.config(text=info["label"], fg=info["color"])
        self._lbl_conf_text.config(
            text=f"Confidence  {int(self._confidence*100)}%" if self._confidence > 0
            else "Collecting data…",
            fg=TEXT2 if self._confidence > 0 else TEXT3)

        features = self.monitor.get_features()
        self._var_keystrokes.set(str(self.monitor.keystroke_count))
        if features:
            self._var_dwell.set(f"{features['D1U1_mean']:.1f} ms")
            self._var_flight.set(f"{features['D1D2_mean']:.1f} ms")
        self._var_duration.set(f"{m}m {s}s")
        self._update_recovery_card()

        n = self.monitor.keystroke_count
        if self._prediction_active:
            if n < self.MIN_KEYSTROKES:
                self._setstatus(f"Need {self.MIN_KEYSTROKES-n} more keystrokes…",
                                TEXT2, "gray")
            else:
                self._setstatus("Detection active — type anywhere", GREEN, "green")

        self._update_history()

    def _refresh_music_ui(self):
        if not self._last_suggestion:
            return
        s    = self._last_suggestion
        info = EMOTIONS.get(self._current_emotion, EMOTIONS["N"])
        self._lbl_song_desc.config(text=info["label"] + "  ·  " + s.description)
        self._lbl_song_title.config(text=s.title)
        self._lbl_song_artist.config(text=s.artist)
        self._btn_play.config(state="normal")
        self._draw_art(self._current_emotion)

    def _update_history(self):
        for w in self._history_frame.winfo_children():
            w.destroy()
        recent = self._emotion_history[-7:]
        if not recent:
            tk.Label(self._history_frame, text="No detections yet",
                     font=(FONT,10), bg=BG2, fg=TEXT3).pack(pady=8)
            return
        for entry in reversed(recent):
            ts, code = entry[0], entry[1]
            info = EMOTIONS.get(code, EMOTIONS["N"])
            row  = tk.Frame(self._history_frame, bg=BG2)
            row.pack(fill="x", pady=2)
            pill = tk.Frame(row, bg=info["color"], width=4)
            pill.pack(side="left", fill="y", padx=(0,8))
            pill.pack_propagate(False)
            tk.Label(row, text=info["label"][0], font=(FONT,13,"bold"),
                     bg=BG2, fg=info["color"]).pack(side="left")
            tk.Label(row, text=" " + info["label"],
                     font=(FONT,10,"bold"), bg=BG2,
                     fg=info["color"]).pack(side="left", padx=2)
            tk.Label(row, text=ts.strftime("%H:%M:%S"),
                     font=(FONT,9), bg=BG2, fg=TEXT3).pack(side="right")

    # ── Charts ────────────────────────────────────────────────────────────────

    _EMOTION_Y      = {"C":1,"N":2,"H":3,"S":4,"A":5}
    _EMOTION_YTICKS = {1:"Calm",2:"Neutral",3:"Happy",4:"Stressed",5:"Angry"}

    def _rebuild_chart(self):
        try:
            if self._canvas:
                self._canvas.get_tk_widget().destroy()
                self._canvas = None
            if self._fig:
                plt.close(self._fig)
                self._fig = None
        except Exception:
            self._canvas = self._fig = None
        {"timeline": self._draw_timeline,
         "pie":      self._draw_pie,
         "dwell":    self._draw_dwell}[self._chart_tab.get()]()

    def _make_fig(self):
        fig, ax = plt.subplots(figsize=(9,2.0), facecolor=BG2)
        ax.set_facecolor(BG3)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        ax.tick_params(colors=TEXT3, labelsize=8)
        ax.title.set_color(TEXT3)
        fig.tight_layout(pad=1.2)
        return fig, ax

    def _embed(self, fig):
        try:
            c = FigureCanvasTkAgg(fig, master=self._chart_frame)
            c.draw()
            w = c.get_tk_widget()
            w.configure(bg=BG2)
            w.pack(fill="both", expand=True)
            self._fig    = fig
            self._canvas = c
        except Exception as e:
            print(f"Chart: {e}")

    def _draw_timeline(self):
        fig, ax = self._make_fig()
        h = self._emotion_history
        if len(h) < 2:
            ax.text(0.5,0.5,"Type for a while to see your emotion timeline",
                    ha="center",va="center",color=TEXT3,fontsize=9,
                    transform=ax.transAxes)
            ax.set_axis_off(); self._embed(fig); return
        times  = [e[0] for e in h]
        ycodes = [self._EMOTION_Y.get(e[1],2) for e in h]
        colors = [EMOTIONS.get(e[1],EMOTIONS["N"])["color"] for e in h]
        ax.step([mdates.date2num(t) for t in times], ycodes,
                where="post", color=BG4, linewidth=1, zorder=1)
        for x,y,c in zip(times,ycodes,colors):
            ax.scatter(mdates.date2num(x),y,color=c,s=60,zorder=2,linewidths=0)
        ax.axhspan(3.5,5.5,alpha=0.06,color=ACCENT,zorder=0)
        ax.axhspan(0.5,1.5,alpha=0.06,color=GREEN, zorder=0)
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_yticks(list(self._EMOTION_YTICKS))
        ax.set_yticklabels(list(self._EMOTION_YTICKS.values()),
                           color=TEXT2,fontsize=8)
        ax.set_ylim(0.5,5.5)
        ax.set_title("Emotion over time",fontsize=9,pad=4)
        fig.autofmt_xdate(rotation=0,ha="center")
        self._embed(fig)

    def _draw_pie(self):
        fig, ax = self._make_fig()
        if not self._emotion_history:
            ax.text(0.5,0.5,"No data yet",ha="center",va="center",
                    color=TEXT3,fontsize=9,transform=ax.transAxes)
            ax.set_axis_off(); self._embed(fig); return
        from collections import Counter
        counts = Counter(e[1] for e in self._emotion_history)
        order  = ["C","H","N","S","A"]
        labels = [EMOTIONS[k]["label"] for k in order if k in counts]
        sizes  = [counts[k]            for k in order if k in counts]
        colors = [EMOTIONS[k]["color"] for k in order if k in counts]
        wedges,texts,autotexts = ax.pie(
            sizes,labels=labels,colors=colors,autopct="%1.0f%%",
            startangle=140,textprops={"color":TEXT2,"fontsize":8},
            wedgeprops={"linewidth":0.5,"edgecolor":BG2})
        for at in autotexts:
            at.set_color(TEXT1); at.set_fontsize(8)
        ax.set_title("Emotion distribution",fontsize=9,pad=4)
        self._embed(fig)

    def _draw_dwell(self):
        fig, ax = self._make_fig()
        pts = [(e[0],e[2]) for e in self._emotion_history if e[2] is not None]
        if len(pts) < 2:
            ax.text(0.5,0.5,"Not enough data yet",ha="center",va="center",
                    color=TEXT3,fontsize=9,transform=ax.transAxes)
            ax.set_axis_off(); self._embed(fig); return
        xs = [mdates.date2num(ts) for ts,_ in pts]
        ys = [d for _,d in pts]
        ax.fill_between(xs,ys,alpha=0.15,color=ACCENT2)
        ax.plot(xs,ys,color=ACCENT2,linewidth=1.5)
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.set_ylabel("ms",color=TEXT3,fontsize=8)
        ax.set_title("Mean dwell time — lower = faster typing",fontsize=9,pad=4)
        fig.autofmt_xdate(rotation=0,ha="center")
        self._embed(fig)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _play_music(self):
        if self._last_suggestion:
            self.recommender.play(self._last_suggestion)

    def _refresh_recommendation(self):
        if self._current_emotion:
            self._last_suggestion = self.recommender.recommend(self._current_emotion)
            self._refresh_music_ui()

    def _do_recalibrate(self):
        was = self._prediction_active
        if was:
            self._prediction_active = False
            self.monitor.stop()
        def after(calib):
            self._calibration = calib
            self.predictor.set_calibration(calib)
            if was:
                self.monitor = KeyboardMonitor()
                self.monitor.start()
                self._prediction_active = True
                self._schedule_predict()
                self._schedule_ui_update()
            self._setstatus(f"Re-calibrated ({calib.calibrated_at})", GREEN, "green")
        force_recalibrate(self.root, after)

    def _generate_report(self):
        """Generate a weekly PDF report and open it, in a background thread."""
        import threading, webbrowser, os
        self._setstatus("Generating report…", YELLOW, "yellow")

        def worker():
            try:
                path = generate_report(days=7)
                if path is None:
                    self.root.after(0, lambda: self._setstatus(
                        "Not enough data yet — keep using StressKey", YELLOW, "yellow"))
                    return
                abspath = os.path.abspath(path)
                webbrowser.open(f"file://{abspath}")
                self.root.after(0, lambda: self._setstatus(
                    f"Report saved: {os.path.basename(path)}", GREEN, "green"))
            except Exception as e:
                self.root.after(0, lambda: self._setstatus(
                    f"Report failed: {e}", ACCENT, "red"))

        threading.Thread(target=worker, daemon=True).start()

    def _stop(self):
        self._prediction_active = False
        self.monitor.stop()
        if self._tray:
            try: self._tray.stop()
            except Exception: pass
            self._tray = None
        self._setstatus("Monitoring stopped", ACCENT, "red")
        self._btn_play.config(state="disabled")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    app  = StressKeyApp(root)

    if TRAY_AVAILABLE:
        def show(): root.after(0, lambda: (root.deiconify(), root.lift(), root.focus_force()))
        def quit_app():
            app._tray.stop(); app._stop(); root.after(0, root.destroy)
        app._tray = TrayIcon(on_show=show,
                             on_play=lambda: root.after(0, app._play_music),
                             on_quit=quit_app)
        app._tray.start()
        def on_close():
            root.withdraw()
            if app._tray:
                app._tray.update_emotion(app._current_emotion,
                    app._last_suggestion.title if app._last_suggestion else "—")
        root.protocol("WM_DELETE_WINDOW", on_close)
    else:
        root.protocol("WM_DELETE_WINDOW", lambda: (app._stop(), root.destroy()))

    root.mainloop()

if __name__ == "__main__":
    main()
