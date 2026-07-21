import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import type { HistoryEntry } from "../hooks/useStressSocket";
import { EMOTION_THEME } from "../lib/emotionTheme";

interface Props {
  history: HistoryEntry[];
  currentEmotion: HistoryEntry["code"];
}

type RangeKey = "1H" | "4H" | "1D";
const RANGE_MS: Record<RangeKey, number> = {
  "1H": 60 * 60 * 1000,
  "4H": 4 * 60 * 60 * 1000,
  "1D": 24 * 60 * 60 * 1000,
};

// Maps emotion to a y-axis "valence" position purely for the chart shape —
// calmer states sit higher, more agitated states sit lower.
const VALENCE: Record<HistoryEntry["code"], number> = {
  C: 0.85,
  H: 0.7,
  N: 0.5,
  S: 0.25,
  A: 0.12,
};

export default function NeuralFlowChart({ history, currentEmotion }: Props) {
  const [range, setRange] = useState<RangeKey>("1H");
  const theme = EMOTION_THEME[currentEmotion];

  const points = useMemo(() => {
    const cutoff = Date.now() - RANGE_MS[range];
    const filtered = history.filter((h) => new Date(h.ts).getTime() >= cutoff);
    const usable = filtered.length >= 2 ? filtered : history.slice(-8);
    if (usable.length < 2) return [];

    const tMin = new Date(usable[0].ts).getTime();
    const tMax = new Date(usable[usable.length - 1].ts).getTime();
    const span = Math.max(1, tMax - tMin);

    return usable.map((h) => {
      const t = new Date(h.ts).getTime();
      const x = ((t - tMin) / span) * 100;
      const y = (1 - VALENCE[h.code]) * 100;
      return { x, y, code: h.code };
    });
  }, [history, range]);

  const pathD = useMemo(() => {
    if (points.length < 2) return "";
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
      .join(" ");
  }, [points]);

  const areaD = useMemo(() => {
    if (points.length < 2) return "";
    const top = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
      .join(" ");
    return `${top} L 100 100 L 0 100 Z`;
  }, [points]);

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0d1411] p-5">
      <div className="mb-1 flex items-center justify-between">
        <p className="font-sora text-[13px] font-semibold text-white/85">Neural Flow</p>
        <div className="flex gap-1 rounded-full bg-white/[0.05] p-0.5">
          {(["1H", "4H", "1D"] as RangeKey[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className="rounded-full px-2.5 py-1 font-sora text-[10px] font-medium transition-colors"
              style={{
                backgroundColor: range === r ? "rgba(255,255,255,0.10)" : "transparent",
                color: range === r ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.4)",
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <p className="mb-3 font-sora text-[11px] font-medium" style={{ color: theme.glow }}>
        {theme.label}
      </p>

      <div className="relative h-[120px] w-full">
        {points.length < 2 ? (
          <div className="flex h-full items-center justify-center">
            <p className="font-sora text-[12px] text-white/30">
              Keep typing — your flow will appear here
            </p>
          </div>
        ) : (
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            className="h-full w-full"
          >
            <defs>
              <linearGradient id="flow-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={theme.glow} stopOpacity="0.25" />
                <stop offset="100%" stopColor={theme.glow} stopOpacity="0" />
              </linearGradient>
              <filter id="flow-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="1.6" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <motion.path
              d={areaD}
              fill="url(#flow-fill)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6 }}
            />
            <motion.path
              d={pathD}
              fill="none"
              stroke={theme.glow}
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
              filter="url(#flow-glow)"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
            />

            {/* Endpoint marker */}
            {points.length > 0 && (
              <circle
                cx={points[points.length - 1].x}
                cy={points[points.length - 1].y}
                r="1.8"
                fill="white"
                filter="url(#flow-glow)"
              />
            )}
          </svg>
        )}
      </div>
    </div>
  );
}
