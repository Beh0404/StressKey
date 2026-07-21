import { motion } from "framer-motion";
import type { HistoryEntry } from "../hooks/useStressSocket";
import { EMOTION_THEME, timeAgo } from "../lib/emotionTheme";

interface Props {
  history: HistoryEntry[];
}

export default function MoodStream({ history }: Props) {
  const recent = [...history].reverse().slice(0, 6);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="w-full max-w-[220px]"
    >
      <p className="mb-4 font-sora text-[10px] font-medium uppercase tracking-[0.18em] text-white/40">
        Mood stream
      </p>

      {recent.length === 0 ? (
        <p className="font-sora text-[12px] text-white/30">
          Your timeline will appear here
        </p>
      ) : (
        <ul className="relative space-y-4 before:absolute before:left-[3px] before:top-1
                       before:bottom-1 before:w-px before:bg-white/10">
          {recent.map((entry, i) => {
            const theme = EMOTION_THEME[entry.code];
            return (
              <motion.li
                key={entry.ts + i}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + i * 0.06, duration: 0.5 }}
                className="relative flex items-center gap-3 pl-0"
              >
                <span
                  className="relative z-10 block h-[7px] w-[7px] shrink-0 rounded-full"
                  style={{
                    backgroundColor: theme.glow,
                    boxShadow: i === 0 ? `0 0 10px ${theme.glow}` : "none",
                  }}
                />
                <div className="flex flex-col">
                  <span
                    className="font-sora text-[12px] font-medium"
                    style={{ color: i === 0 ? theme.glow : "rgba(255,255,255,0.7)" }}
                  >
                    {theme.label}
                  </span>
                  <span className="font-sora text-[10px] text-white/35">
                    {timeAgo(entry.ts)}
                  </span>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </motion.div>
  );
}
