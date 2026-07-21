"""
StressKey - System Tray Module
Runs a pystray icon in a background thread.
Clicking the icon shows/hides the main window.
Right-click menu shows current emotion + quick actions.
"""

import threading
import pystray
from PIL import Image, ImageDraw, ImageFont


# ── Emotion → tray icon colour ────────────────────────────────────────────────
EMOTION_COLOURS = {
    "S": "#FF6B6B",   # Stressed  — red
    "A": "#FF4500",   # Angry     — orange-red
    "N": "#4ECDC4",   # Neutral   — teal
    "H": "#FFD93D",   # Happy     — yellow
    "C": "#6BCB77",   # Calm      — green
}

EMOTION_LABELS = {
    "S": "Stressed 😰",
    "A": "Angry 😠",
    "N": "Neutral 😐",
    "H": "Happy 😊",
    "C": "Calm 😌",
}


def _hex_to_rgb(hex_colour: str) -> tuple:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _make_icon(emotion_code: str, size: int = 64) -> Image.Image:
    """
    Draw a small square icon with:
    - Solid background in the emotion colour
    - A white 'SK' text label centred inside
    """
    colour = EMOTION_COLOURS.get(emotion_code, "#4ECDC4")
    rgb    = _hex_to_rgb(colour)

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-rect background
    margin = 2
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=12,
        fill=rgb + (255,)
    )

    # White 'SK' text centred
    try:
        # Use a decent font if available, else default
        fnt = ImageFont.truetype("segoeui.ttf", size // 3)
    except Exception:
        fnt = ImageFont.load_default()

    text = "SK"
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    tx   = (size - tw) // 2
    ty   = (size - th) // 2 - 2
    draw.text((tx, ty), text, fill=(255, 255, 255, 230), font=fnt)

    return img


class TrayIcon:
    """
    Wraps pystray.Icon and exposes a simple API so gui_app
    doesn't need to know about pystray internals.

    Usage:
        tray = TrayIcon(
            on_show=lambda: ...,   # called when user clicks Show
            on_quit=lambda: ...,   # called when user clicks Quit
        )
        tray.start()               # starts background thread
        tray.update_emotion("S")   # updates icon + menu tooltip
        tray.stop()                # cleans up
    """

    def __init__(self, on_show, on_play, on_quit):
        self._on_show  = on_show
        self._on_play  = on_play
        self._on_quit  = on_quit

        self._emotion  = "N"
        self._song     = "—"
        self._icon     = None
        self._thread   = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Launch the tray icon in a daemon thread."""
        self._icon = pystray.Icon(
            name  = "StressKey",
            icon  = _make_icon(self._emotion),
            title = "StressKey — Monitoring",
            menu  = self._build_menu(),
        )
        self._thread = threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="TrayThread"
        )
        self._thread.start()

    def stop(self):
        """Remove the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def update_emotion(self, emotion_code: str, song_title: str = "—"):
        """Refresh icon colour and menu to reflect new emotion."""
        if not self._icon:
            return
        self._emotion = emotion_code
        self._song    = song_title

        label  = EMOTION_LABELS.get(emotion_code, "Unknown")
        colour = EMOTION_COLOURS.get(emotion_code, "#4ECDC4")

        try:
            self._icon.icon  = _make_icon(emotion_code)
            self._icon.title = f"StressKey  ·  {label}"
            self._icon.menu  = self._build_menu()
        except Exception:
            pass   # tray may not be ready yet

    # ── Menu builder ──────────────────────────────────────────────────────────

    def _build_menu(self):
        emotion_label = EMOTION_LABELS.get(self._emotion, "Detecting…")
        song_label    = f"♪ {self._song[:36]}…" if len(self._song) > 36 \
                        else f"♪ {self._song}"

        return pystray.Menu(
            # ── Status (non-clickable) ──
            pystray.MenuItem(
                f"Emotion: {emotion_label}",
                action=None,
                enabled=False
            ),
            pystray.MenuItem(
                song_label,
                action=None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,

            # ── Actions ──
            pystray.MenuItem(
                "Show StressKey",
                action=lambda icon, item: self._on_show(),
                default=True,   # double-click action
            ),
            pystray.MenuItem(
                "▶  Play recommended music",
                action=lambda icon, item: self._on_play(),
            ),
            pystray.Menu.SEPARATOR,

            pystray.MenuItem(
                "Quit",
                action=lambda icon, item: self._on_quit(),
            ),
        )
