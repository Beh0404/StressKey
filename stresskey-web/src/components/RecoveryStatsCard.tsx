import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Timer, TrendingDown } from "lucide-react";

interface RecoveryStats {
  has_data: boolean;
  total_episodes?: number;
  resolved_count?: number;
  resolution_rate?: number;
  avg_recovery_seconds?: number | null;
  fastest_seconds?: number | null;
  active_episode_seconds?: number | null;
}

const API_URL = "http://localhost:8000/api/recovery/stats?days=7";
const POLL_MS = 20000;

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "—";
  const s = Math.round(seconds);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return m === 0 ? `${rem}s` : `${m}m ${rem}s`;
}

/**
 * RecoveryStatsCard — displays intervention effectiveness metrics:
 * how quickly the user's detected stress episodes resolve back to
 * a calm/neutral/happy state after a music intervention begins.
 *
 * Methodological note (shown in-card): this measures observed
 * time-to-recovery, not a proven causal effect of the music itself,
 * since no no-intervention control condition is recorded.
 */
export default function RecoveryStatsCard({ accent }: { accent: string }) {
  const [stats, setStats] = useState<RecoveryStats | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (!cancelled) setStats(data);
      } catch {
        // Backend not reachable — leave stats as-is, will retry next tick
      }
    }

    poll();
    const id = setInterval(poll, POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0d1411] p-5">
      <div className="mb-1 flex items-center gap-2">
        <Timer className="h-3.5 w-3.5" style={{ color: accent }} />
        <p className="font-sora text-[13px] font-semibold text-white/85">
          Recovery Time
        </p>
      </div>

      {!stats?.has_data ? (
        <p className="mt-3 font-sora text-[12px] text-white/30">
          No stress episodes recorded yet this week.
        </p>
      ) : (
        <>
          <div className="mt-3 flex items-end gap-2">
            <motion.span
              key={stats.avg_recovery_seconds}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="font-sora text-[28px] font-bold"
              style={{ color: accent }}
            >
              {formatDuration(stats.avg_recovery_seconds)}
            </motion.span>
            <span className="mb-1 font-sora text-[11px] text-white/40">
              avg recovery
            </span>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2">
            <div>
              <p className="font-sora text-[15px] font-semibold text-white/80">
                {stats.total_episodes}
              </p>
              <p className="font-sora text-[9.5px] text-white/35">Episodes</p>
            </div>
            <div>
              <p className="font-sora text-[15px] font-semibold text-white/80">
                {stats.resolution_rate?.toFixed(0)}%
              </p>
              <p className="font-sora text-[9.5px] text-white/35">Resolved</p>
            </div>
            <div>
              <p className="font-sora text-[15px] font-semibold text-white/80">
                {formatDuration(stats.fastest_seconds)}
              </p>
              <p className="font-sora text-[9.5px] text-white/35">Fastest</p>
            </div>
          </div>

          {stats.active_episode_seconds != null && (
            <div className="mt-3 flex items-center gap-1.5 rounded-lg bg-white/[0.04] px-2.5 py-1.5">
              <TrendingDown className="h-3 w-3 text-orange-400" />
              <span className="font-sora text-[10.5px] text-white/60">
                Active episode: {formatDuration(stats.active_episode_seconds)} elapsed
              </span>
            </div>
          )}

          <p className="mt-3 font-sora text-[9px] leading-relaxed text-white/25">
            Measures time between a stress detection and the next calm/neutral
            state. Reflects observed recovery, not a proven causal effect of
            the music intervention itself.
          </p>
        </>
      )}
    </div>
  );
}
