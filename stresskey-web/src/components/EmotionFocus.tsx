import { motion, AnimatePresence } from "framer-motion";
import type { EmotionCode } from "../hooks/useStressSocket";
import { EMOTION_THEME } from "../lib/emotionTheme";

interface Props {
  emotion: EmotionCode;
  confidence: number;
  monitoringActive: boolean;
  keystrokesNeeded: number | null; // null = enough data collected
}

export default function EmotionFocus({
  emotion,
  confidence,
  monitoringActive,
  keystrokesNeeded,
}: Props) {
  const theme = EMOTION_THEME[emotion];
  const pct = Math.round(confidence * 100);

  return (
    <div className="relative flex flex-col items-center justify-center select-none">
      {/* Organic light bloom - the breathing core */}
      <div
        className="pointer-events-none absolute -z-10 h-[420px] w-[420px] rounded-full blur-3xl animate-breathe"
        style={{
          background: `radial-gradient(circle, ${theme.glowSoft} 0%, transparent 70%)`,
        }}
      />
      <div
        className="pointer-events-none absolute -z-10 h-[640px] w-[640px] rounded-full blur-[80px] animate-breathe-slow"
        style={{
          background: `radial-gradient(circle, ${theme.glowSoft} 0%, transparent 65%)`,
          opacity: 0.5,
        }}
      />

      {/* Emotion word */}
      <AnimatePresence mode="wait">
        <motion.h1
          key={emotion}
          initial={{ opacity: 0, y: 14, filter: "blur(6px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="font-sora text-[64px] sm:text-[88px] lg:text-[104px] font-semibold tracking-tight leading-none text-white"
          style={{
            textShadow: `0 0 60px ${theme.textGlow}, 0 0 120px ${theme.textGlow}`,
          }}
        >
          {theme.label}
        </motion.h1>
      </AnimatePresence>

      {/* Confidence / status line */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="mt-5 flex items-center gap-2.5"
      >
        <span
          className="h-[6px] w-[6px] rounded-full"
          style={{ backgroundColor: theme.glow, boxShadow: `0 0 10px ${theme.glow}` }}
        />
        <span className="font-sora text-[11px] font-medium uppercase tracking-[0.18em] text-white/55">
          {!monitoringActive
            ? "Monitoring paused"
            : keystrokesNeeded !== null
            ? `Calibrating — ${keystrokesNeeded} keystrokes to go`
            : `Confidence · ${pct}%`}
        </span>
      </motion.div>

      {/* Minimal breathing progress indicator */}
      {monitoringActive && keystrokesNeeded === null && (
        <div className="mt-4 h-[2px] w-[180px] overflow-hidden rounded-full bg-white/10">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: theme.glow }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </div>
      )}
    </div>
  );
}
