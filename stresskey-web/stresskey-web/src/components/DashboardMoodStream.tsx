import { motion } from "framer-motion";
import type { HistoryEntry } from "../hooks/useStressSocket";
import { EMOTION_THEME, timeAgo } from "../lib/emotionTheme";

interface Props {
  history: HistoryEntry[];
}

function describeTransition(prevLabel: string | null, label: string): string {
  if (!prevLabel) return `${label} detected`;
  if (prevLabel === label) return `${label} sustained`;
  return `${prevLabel} → ${label}`;
}

export default function DashboardMoodStream({ history }: Props) {
  const recent = [...history].reverse().slice(0, 4);
  const original = [...history];

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0d1411] p-5">
      <p className="mb-4 font-sora text-[13px] font-semibold text-white/85">
        Mood Stream
      </p>

      {recent.length === 0 ? (
        <p className="font-sora text-[12px] text-white/30">No transitions logged yet</p>
      ) : (
        <ul className="flex flex-col gap-3.5">
          {recent.map((entry, i) => {
            const theme = EMOTION_THEME[entry.code];
            const idxInOriginal = original.length - 1 - i;
            const prevEntry = original[idxInOriginal - 1];
            const prevLabel = prevEntry ? EMOTION_THEME[prevEntry.code].label : null;

            return (
              <motion.li
                key={entry.ts + i}
                initial={{ opacity: 0, x: 6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                className="flex items-start gap-2.5"
              >
                <span
                  className="mt-1.5 block h-[6px] w-[6px] shrink-0 rounded-full"
                  style={{
                    backgroundColor: theme.glow,
                    boxShadow: i === 0 ? `0 0 8px ${theme.glow}` : "none",
                  }}
                />
                <div>
                  <p className="font-sora text-[12px] font-medium text-white/80">
                    {describeTransition(prevLabel, theme.label)}
                  </p>
                  <p className="font-sora text-[10.5px] text-white/35">
                    {timeAgo(entry.ts)}
                  </p>
                </div>
              </motion.li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
