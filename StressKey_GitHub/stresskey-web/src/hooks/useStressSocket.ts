import { useCallback, useEffect, useRef, useState } from "react";

export type EmotionCode = "S" | "A" | "N" | "H" | "C";

export interface MusicPayload {
  title: string;
  artist: string;
  url: string;
  description: string;
  emoji: string;
  color: string;
  label: string;
}

export interface HistoryEntry {
  ts: string;
  code: EmotionCode;
  dwell: number | null;
}

export interface StressState {
  connected: boolean;
  monitoringActive: boolean;
  emotion: EmotionCode;
  confidence: number;
  proba: Partial<Record<EmotionCode, number>>;
  keystrokes: number;
  sessionSeconds: number;
  isCalibrated: boolean;
  calibratedAt: string | null;
  music: MusicPayload | null;
  history: HistoryEntry[];
  dwellMs: number | null;
  flightMs: number | null;
}

const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY_MS = 2000;

const initialState: StressState = {
  connected: false,
  monitoringActive: false,
  emotion: "N",
  confidence: 0,
  proba: {},
  keystrokes: 0,
  sessionSeconds: 0,
  isCalibrated: false,
  calibratedAt: null,
  music: null,
  history: [],
  dwellMs: null,
  flightMs: null,
};

export function useStressSocket() {
  const [state, setState] = useState<StressState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const send = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        setState((s) => ({ ...s, connected: true }));
      };

      ws.onclose = () => {
        if (cancelled) return;
        setState((s) => ({ ...s, connected: false }));
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const msg = JSON.parse(event.data);
          applyMessage(msg, setState);
        } catch {
          // ignore malformed frames
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  const startMonitoring = useCallback(() => send({ action: "start_monitoring" }), [send]);
  const stopMonitoring  = useCallback(() => send({ action: "stop_monitoring" }),  [send]);
  const playMusic       = useCallback(() => send({ action: "play_music" }),       [send]);
  const refreshMusic    = useCallback(() => send({ action: "refresh_music" }),    [send]);

  return { state, send, startMonitoring, stopMonitoring, playMusic, refreshMusic };
}

function applyMessage(
  msg: any,
  setState: React.Dispatch<React.SetStateAction<StressState>>
) {
  switch (msg.type) {
    case "snapshot": {
      setState((s) => ({
        ...s,
        emotion: msg.emotion,
        confidence: msg.confidence,
        proba: msg.proba ?? {},
        keystrokes: msg.keystrokes,
        sessionSeconds: msg.session_seconds,
        monitoringActive: msg.monitoring_active,
        isCalibrated: msg.is_calibrated,
        calibratedAt: msg.calibrated_at,
        music: msg.music,
        history: msg.history ?? [],
      }));
      break;
    }
    case "prediction": {
      setState((s) => ({
        ...s,
        emotion: msg.emotion,
        confidence: msg.confidence,
        proba: msg.proba ?? {},
        keystrokes: msg.keystrokes,
        music: msg.music ?? s.music,
        dwellMs: msg.features?.dwell_ms ?? s.dwellMs,
        flightMs: msg.features?.flight_ms ?? s.flightMs,
        history: msg.changed
          ? [
              ...s.history,
              { ts: new Date().toISOString(), code: msg.emotion, dwell: msg.features?.dwell_ms ?? null },
            ].slice(-30)
          : s.history,
      }));
      break;
    }
    case "tick": {
      setState((s) => ({
        ...s,
        sessionSeconds: msg.session_seconds,
        keystrokes: msg.keystrokes,
        monitoringActive: msg.monitoring_active,
      }));
      break;
    }
    case "status": {
      setState((s) => ({ ...s, monitoringActive: msg.monitoring_active }));
      break;
    }
    case "music_update": {
      setState((s) => ({ ...s, music: msg.music }));
      break;
    }
    default:
      break;
  }
}
