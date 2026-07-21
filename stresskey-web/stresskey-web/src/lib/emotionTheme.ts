import type { EmotionCode } from "../hooks/useStressSocket";

export interface EmotionTheme {
  label: string;
  glow: string;       // hex used for glow / accent
  glowSoft: string;   // rgba string for radial gradients
  textGlow: string;   // text-shadow color
}

export const EMOTION_THEME: Record<EmotionCode, EmotionTheme> = {
  C: {
    label: "Calm",
    glow: "#34e7b8",
    glowSoft: "rgba(52,231,184,0.35)",
    textGlow: "rgba(52,231,184,0.55)",
  },
  H: {
    label: "Happy",
    glow: "#ffd166",
    glowSoft: "rgba(255,209,102,0.32)",
    textGlow: "rgba(255,209,102,0.5)",
  },
  N: {
    label: "Neutral",
    glow: "#7eb6ff",
    glowSoft: "rgba(126,182,255,0.30)",
    textGlow: "rgba(126,182,255,0.45)",
  },
  S: {
    label: "Stressed",
    glow: "#ff6b6b",
    glowSoft: "rgba(255,107,107,0.32)",
    textGlow: "rgba(255,107,107,0.5)",
  },
  A: {
    label: "Angry",
    glow: "#ff8c4b",
    glowSoft: "rgba(255,140,75,0.34)",
    textGlow: "rgba(255,140,75,0.5)",
  },
};

export function formatClock(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Now";
  if (mins === 1) return "1 min ago";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

/**
 * Derives Focus / Stress / Fatigue percentages from the model's real
 * probability distribution — not invented numbers. This keeps the
 * dashboard's "Current Vector" panel honest about what the model
 * actually output.
 *
 *   Stress  = P(Stressed) + P(Angry)
 *   Focus   = P(Calm) + P(Neutral)  — states associated with steady typing
 *   Fatigue = inverse of overall confidence — low confidence reads as
 *             noisier, more erratic typing rhythm
 */
export function deriveVector(
  proba: Partial<Record<EmotionCode, number>>,
  confidence: number
) {
  const stress = (proba.S ?? 0) + (proba.A ?? 0);
  const focus = (proba.C ?? 0) + (proba.N ?? 0) + (proba.H ?? 0) * 0.5;
  const fatigue = Math.max(0, 1 - confidence) * 0.7 + stress * 0.3;

  return {
    focus: Math.round(Math.min(1, focus) * 100),
    stress: Math.round(Math.min(1, stress) * 100),
    fatigue: Math.round(Math.min(1, fatigue) * 100),
  };
}
