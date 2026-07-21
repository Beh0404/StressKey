# StressKey Web

The browser frontend for StressKey — a glassmorphic, immersive
emotion-monitoring + music-recommendation interface.

This is the **web frontend only**. The Python backend (keyboard
monitoring + ML prediction + music recommendations) lives in the
`StressKey` desktop project folder and must run alongside this app.

## Architecture

```
StressKey/server.py  (Python, port 8000)
   keyboard_monitor.py  → listens to keystrokes
   emotion_predictor.py → ML prediction
   music_recommender.py → music suggestions
        │
        │  WebSocket  ws://localhost:8000/ws
        ▼
stresskey-web/  (this project, port 5173)
   React + TypeScript + Tailwind + Framer Motion
```

## Run both halves

**Terminal 1 — backend:**
```bash
cd StressKey
pip install fastapi uvicorn websockets
python server.py
```

**Terminal 2 — frontend:**
```bash
cd stresskey-web
npm install
npm run dev
```

Then open **http://localhost:5173**.

## Design notes

- Font: Sora (geometric sans), loaded via Google Fonts in `index.html`
- Palette: near-black void background (`#020207` → `#06060f`) with an
  organic, slowly drifting light bloom tinted by the current emotion
- Glass surfaces: `backdrop-blur` 40px+, thin white rim-light borders
- Signature element: the central "breathing" glow behind the emotion
  word — pulses on a 6s/9s dual-layer cycle, recolors per emotion
- Motion: Framer Motion handles cross-fades on emotion change, staggered
  entrance for the music card and mood stream, and the glow's
  ambient drift

## Folder structure

```
src/
  App.tsx                    — composes the full screen
  index.css                  — Tailwind directives + base styles
  hooks/
    useStressSocket.ts        — WebSocket client + reconnect logic
  lib/
    emotionTheme.ts           — emotion → color/label token map
  components/
    TopBar.tsx                 — connection dot, session timer, pause/play
    EmotionFocus.tsx            — the breathing glow + emotion word (hero)
    MusicCard.tsx               — glass music environment card
    MoodStream.tsx              — vertical timeline of recent emotions
```
