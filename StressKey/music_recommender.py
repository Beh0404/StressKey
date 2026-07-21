"""
StressKey - Music Recommender Module
Maps predicted emotion → search query → YouTube Music link
Opens the link in the default browser automatically.
"""

import webbrowser
import urllib.parse
from dataclasses import dataclass
from typing import Optional


@dataclass
class MusicSuggestion:
    emotion:      str
    title:        str
    artist:       str
    url:          str
    description:  str
    emoji:        str


# ── Emotion → Music mapping ────────────────────────────────────────────────
# Based on the Iso Principle: match current state, then guide toward calm.

EMOTION_MUSIC_MAP = {
    "S": {   # Stressed
        "emoji":       "😰",
        "label":       "Stressed",
        "color":       "#FF6B6B",
        "description": "Calming music to ease your stress",
        "queries": [
            "calming piano music for stress relief",
            "lo-fi beats to relax study",
            "ambient relaxation music",
            "peaceful nature sounds music",
        ],
        "yt_playlist": "PLWNHDKBNBkD-xTT2i7GvpNwb1TymKa_V_",  # fallback
    },
    "A": {   # Angry
        "emoji":       "😠",
        "label":       "Angry",
        "color":       "#FF4500",
        "description": "Music to channel your energy and find calm",
        "queries": [
            "calming music after anger meditation",
            "slow deep breathing music",
            "soft instrumental music calm",
            "ocean waves relaxing music",
        ],
    },
    "N": {   # Neutral
        "emoji":       "😐",
        "label":       "Neutral",
        "color":       "#4ECDC4",
        "description": "Focus music for productivity",
        "queries": [
            "focus music for work and study",
            "lo-fi hip hop beats",
            "concentration background music",
            "productivity instrumental music",
        ],
    },
    "H": {   # Happy
        "emoji":       "😊",
        "label":       "Happy",
        "color":       "#FFD93D",
        "description": "Upbeat music to keep the good vibes going",
        "queries": [
            "upbeat happy feel good music playlist",
            "positive energy music",
            "feel good pop hits",
            "happy vibes music mix",
        ],
    },
    "C": {   # Calm
        "emoji":       "😌",
        "label":       "Calm",
        "color":       "#6BCB77",
        "description": "Gentle music to maintain your calm state",
        "queries": [
            "peaceful ambient music",
            "gentle acoustic guitar music",
            "spa relaxation music",
            "soft piano music calm",
        ],
    },
}


class MusicRecommender:
    """Recommends and opens YouTube Music based on detected emotion."""

    def __init__(self):
        self._ytmusic    = None
        self._last_query = None
        self._query_index = {}   # emotion → current query index
        self._init_ytmusic()

    def _init_ytmusic(self):
        """Try to initialise ytmusicapi (optional - graceful fallback)."""
        try:
            from ytmusicapi import YTMusic
            # Unauthenticated - search only, no account needed
            self._ytmusic = YTMusic()
            print("✅ ytmusicapi initialised (unauthenticated search)")
        except Exception as e:
            print(f"⚠️  ytmusicapi not available ({e}). Using YouTube search fallback.")
            self._ytmusic = None

    def get_emotion_info(self, emotion_code: str) -> dict:
        return EMOTION_MUSIC_MAP.get(emotion_code, EMOTION_MUSIC_MAP["N"])

    def recommend(self, emotion_code: str) -> MusicSuggestion:
        """
        Returns a MusicSuggestion for the given emotion code.
        Rotates through queries to provide variety.
        """
        info    = self.get_emotion_info(emotion_code)
        queries = info["queries"]

        # Rotate query index for variety
        idx = self._query_index.get(emotion_code, 0)
        query = queries[idx % len(queries)]
        self._query_index[emotion_code] = (idx + 1) % len(queries)

        # Try ytmusicapi first
        if self._ytmusic is not None:
            try:
                return self._search_ytmusic(query, emotion_code, info)
            except Exception as e:
                print(f"⚠️  ytmusicapi search failed: {e}")

        # Fallback: YouTube search URL
        return self._youtube_search_fallback(query, emotion_code, info)

    def _search_ytmusic(self, query: str, code: str, info: dict) -> MusicSuggestion:
        results = self._ytmusic.search(query, filter="songs", limit=5)
        if not results:
            raise ValueError("No results")

        song   = results[0]
        title  = song.get("title", "Unknown")
        artist = song.get("artists", [{}])[0].get("name", "Unknown")
        vid_id = song.get("videoId", "")
        url    = f"https://music.youtube.com/watch?v={vid_id}" if vid_id else \
                 self._yt_search_url(query)

        return MusicSuggestion(
            emotion=code,
            title=title,
            artist=artist,
            url=url,
            description=info["description"],
            emoji=info["emoji"],
        )

    def _youtube_search_fallback(self, query: str, code: str, info: dict) -> MusicSuggestion:
        url = self._yt_search_url(query)
        return MusicSuggestion(
            emotion=code,
            title=query.title(),
            artist="YouTube Music",
            url=url,
            description=info["description"],
            emoji=info["emoji"],
        )

    @staticmethod
    def _yt_search_url(query: str) -> str:
        q = urllib.parse.quote_plus(query)
        return f"https://music.youtube.com/search?q={q}"

    def play(self, suggestion: MusicSuggestion):
        """Open the music URL in the default browser."""
        webbrowser.open(suggestion.url)
        print(f"🎵 Opening: {suggestion.title} – {suggestion.artist}")
        print(f"   URL: {suggestion.url}")