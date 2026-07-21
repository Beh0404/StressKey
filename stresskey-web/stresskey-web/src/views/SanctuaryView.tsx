import { useMemo } from "react";
import { motion } from "framer-motion";
import type { StressState } from "../hooks/useStressSocket";
import TopBar from "../components/TopBar";
import EmotionFocus from "../components/EmotionFocus";
import MusicCard from "../components/MusicCard";
import MoodStream from "../components/MoodStream";
import { EMOTION_THEME } from "../lib/emotionTheme";

const MIN_KEYSTROKES = 15;

interface Props {
  state: StressState;
  onToggleMonitoring: () => void;
  onPlayMusic: () => void;
  onRefreshMusic: () => void;
}

/**
 * SanctuaryView — the minimal, immersive "breathing glow" design.
 * One emotion word, one glow, two quiet cards. Nothing competes
 * with the central state.
 */
export default function SanctuaryView({
  state,
  onToggleMonitoring,
  onPlayMusic,
  onRefreshMusic,
}: Props) {
  const theme = EMOTION_THEME[state.emotion];

  const keystrokesNeeded = useMemo(() => {
    if (!state.monitoringActive) return null;
    const remaining = MIN_KEYSTROKES - state.keystrokes;
    return remaining > 0 ? remaining : null;
  }, [state.monitoringActive, state.keystrokes]);

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-void-950 font-sora">
      {/* Base gradient wash - black to deep blue-black */}
      <div
        className="pointer-events-none absolute inset-0 -z-20"
        style={{
          background:
            "radial-gradient(120% 90% at 70% 18%, #0c0e22 0%, #06060f 45%, #020207 100%)",
        }}
      />

      {/* Ambient drifting bloom, tinted by current emotion */}
      <motion.div
        key={state.emotion + "-ambient"}
        className="pointer-events-none absolute -z-10 right-[-10%] top-[8%] h-[700px] w-[700px]
                   rounded-full blur-[120px] animate-drift"
        animate={{ opacity: 1 }}
        initial={{ opacity: 0 }}
        transition={{ duration: 1.6 }}
        style={{
          background: `radial-gradient(circle, ${theme.glowSoft} 0%, transparent 70%)`,
        }}
      />

      {/* Film grain / noise vignette for depth */}
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,transparent_40%,rgba(0,0,0,0.55)_100%)]" />

      <div className="relative z-10 flex min-h-screen flex-col">
        <TopBar
          connected={state.connected}
          monitoringActive={state.monitoringActive}
          sessionSeconds={state.sessionSeconds}
          onToggleMonitoring={onToggleMonitoring}
        />

        {/* Hero / emotion core */}
        <div className="flex flex-1 items-center justify-center px-6">
          <EmotionFocus
            emotion={state.emotion}
            confidence={state.confidence}
            monitoringActive={state.monitoringActive}
            keystrokesNeeded={keystrokesNeeded}
          />
        </div>

        {/* Bottom zone: music card (left) + mood stream (right) */}
        <div className="relative z-20 flex flex-col gap-8 px-6 pb-8 sm:flex-row sm:items-end sm:justify-between sm:px-10 sm:pb-10">
          <MusicCard music={state.music} onPlay={onPlayMusic} onRefresh={onRefreshMusic} />
          <MoodStream history={state.history} />
        </div>
      </div>
    </div>
  );
}
