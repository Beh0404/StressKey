import { motion } from "framer-motion";
import { Pause, Play } from "lucide-react";
import { formatClock } from "../lib/emotionTheme";

interface Props {
  connected: boolean;
  monitoringActive: boolean;
  sessionSeconds: number;
  onToggleMonitoring: () => void;
}

export default function TopBar({
  connected,
  monitoringActive,
  sessionSeconds,
  onToggleMonitoring,
}: Props) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      className="relative z-20 flex items-center justify-between px-6 sm:px-10 py-5 sm:pr-56"
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`h-[6px] w-[6px] rounded-full transition-colors ${
            connected ? "bg-emerald-400" : "bg-white/25"
          }`}
          style={connected ? { boxShadow: "0 0 8px rgba(52,231,184,0.8)" } : undefined}
        />
        <span className="font-sora text-[12px] font-medium tracking-wide text-white/60">
          StressKey
        </span>
      </div>

      <div className="flex items-center gap-5">
        <span className="font-sora text-[11px] tabular-nums tracking-wide text-white/35">
          {formatClock(sessionSeconds)}
        </span>
        <button
          onClick={onToggleMonitoring}
          className="flex h-8 w-8 items-center justify-center rounded-full
                     bg-white/[0.06] ring-1 ring-inset ring-white/10 backdrop-blur-xl
                     text-white/60 transition-colors hover:text-white hover:bg-white/[0.12]"
          aria-label={monitoringActive ? "Pause monitoring" : "Start monitoring"}
        >
          {monitoringActive ? (
            <Pause className="h-3 w-3 fill-current" strokeWidth={0} />
          ) : (
            <Play className="h-3 w-3 fill-current" strokeWidth={0} />
          )}
        </button>
      </div>
    </motion.header>
  );
}
