import { motion, AnimatePresence } from "framer-motion";
import { Play } from "lucide-react";
import type { MusicPayload, EmotionCode } from "../hooks/useStressSocket";
import { EMOTION_THEME } from "../lib/emotionTheme";

interface Props {
  emotion: EmotionCode;
  confidence: number;
  music: MusicPayload | null;
  onPlay: () => void;
}

export default function DashboardStateCard({ emotion, confidence, music, onPlay }: Props) {
  const theme = EMOTION_THEME[emotion];
  const pct = Math.round(confidence * 100);

  return (
    <div
      className="relative flex min-w-0 flex-col items-center overflow-hidden rounded-2xl border border-white/[0.06]
                 px-8 py-12"
      style={{
        background: `radial-gradient(120% 100% at 50% 0%, ${theme.glowSoft} 0%, #0a0f0d 55%)`,
      }}
    >
      <span className="font-sora text-[11px] font-semibold uppercase tracking-[0.18em] text-white/40">
        Current state
      </span>

      <AnimatePresence mode="wait">
        <motion.h2
          key={emotion}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="mt-1 font-sora text-[40px] font-bold text-white"
          style={{ textShadow: `0 0 32px ${theme.textGlow}` }}
        >
          {theme.label}
        </motion.h2>
      </AnimatePresence>

      <div className="mt-3 flex items-center gap-1.5">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke={theme.glow} strokeWidth="2" opacity="0.3" />
          <path
            d="M8 12l2.5 2.5L16 9"
            stroke={theme.glow}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="font-sora text-[14px] font-semibold tabular-nums" style={{ color: theme.glow }}>
          {pct}%
        </span>
        <span className="font-sora text-[12px] text-white/45">Confidence</span>
      </div>

      <div className="mt-6 h-[3px] w-full max-w-[280px] overflow-hidden rounded-full bg-white/[0.08]">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: theme.glow }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>

      {/* Mini music player */}
      <div className="mt-10 flex w-full max-w-[300px] items-center gap-3 rounded-xl border border-white/[0.06] bg-black/30 px-3 py-2.5">
        <button
          onClick={onPlay}
          disabled={!music}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-black transition-transform
                     hover:scale-105 active:scale-95 disabled:opacity-30"
          style={{ backgroundColor: theme.glow }}
        >
          <Play className="h-3.5 w-3.5 fill-current" strokeWidth={0} />
        </button>
        <div className="min-w-0">
          <p className="truncate font-sora text-[12.5px] font-medium text-white/85">
            {music?.title ?? "Awaiting signal…"}
          </p>
          <p className="truncate font-sora text-[10.5px] text-white/40">
            {music?.artist ?? "—"}
          </p>
        </div>
      </div>
    </div>
  );
}
