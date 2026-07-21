import { motion } from "framer-motion";
import { Play, RotateCw, ExternalLink } from "lucide-react";
import type { MusicPayload } from "../hooks/useStressSocket";

interface Props {
  music: MusicPayload | null;
  onPlay: () => void;
  onRefresh: () => void;
}

export default function MusicCard({ music, onPlay, onRefresh }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="relative w-full max-w-[360px] overflow-hidden rounded-3xl
                 bg-white/[0.06] backdrop-blur-[40px]
                 ring-1 ring-inset ring-white/[0.10]
                 shadow-[0_8px_40px_rgba(0,0,0,0.35)]"
    >
      {/* Depth-of-field cover art */}
      <div className="relative h-[150px] w-full overflow-hidden">
        <div
          className="absolute inset-0 scale-110 blur-[2px]"
          style={{
            background: music
              ? `radial-gradient(circle at 30% 20%, ${music.color}55, transparent 60%),
                 radial-gradient(circle at 80% 80%, ${music.color}33, transparent 55%),
                 linear-gradient(135deg, rgba(10,10,20,0.9), rgba(5,5,12,0.95))`
              : "linear-gradient(135deg, rgba(20,20,35,0.9), rgba(8,8,16,0.95))",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
        <div className="absolute left-5 top-4">
          <span className="font-sora text-[10px] font-medium uppercase tracking-[0.16em] text-white/55">
            Now playing environment
          </span>
        </div>
        <div className="absolute bottom-4 left-5 right-5">
          <p className="font-sora text-[20px] font-semibold text-white drop-shadow-lg truncate">
            {music?.title ?? "Listening to your rhythm…"}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 px-5 py-4">
        <button
          onClick={onPlay}
          disabled={!music}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full
                     bg-white/90 text-black transition-transform
                     hover:scale-105 active:scale-95 disabled:opacity-30 disabled:hover:scale-100"
          aria-label="Play"
        >
          <Play className="h-4 w-4 fill-current" strokeWidth={0} />
        </button>

        {/* Glowing progress line */}
        <div className="relative flex-1">
          <div className="h-[2px] w-full rounded-full bg-white/15" />
          <motion.div
            className="absolute left-0 top-0 h-[2px] rounded-full"
            style={{
              backgroundColor: music?.color ?? "#7eb6ff",
              boxShadow: `0 0 8px ${music?.color ?? "#7eb6ff"}`,
            }}
            initial={{ width: "0%" }}
            animate={{ width: "38%" }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
        </div>

        <span className="font-sora text-[11px] tabular-nums text-white/45 shrink-0">
          {music ? music.artist.slice(0, 14) : "—"}
        </span>

        <button
          onClick={onRefresh}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                     text-white/45 transition-colors hover:bg-white/10 hover:text-white/80"
          aria-label="Refresh recommendation"
        >
          <RotateCw className="h-3.5 w-3.5" />
        </button>

        {music && (
          <a
            href={music.url}
            target="_blank"
            rel="noreferrer"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                       text-white/45 transition-colors hover:bg-white/10 hover:text-white/80"
            aria-label="Open externally"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
    </motion.div>
  );
}
