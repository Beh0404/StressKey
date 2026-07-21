import { useState } from "react";
import { FileText } from "lucide-react";
import type { StressState } from "../hooks/useStressSocket";
import Sidebar from "../components/Sidebar";
import DashboardStateCard from "../components/DashboardStateCard";
import VectorPanel from "../components/VectorPanel";
import DashboardMoodStream from "../components/DashboardMoodStream";
import RecoveryStatsCard from "../components/RecoveryStatsCard";
import NeuralFlowChart from "../components/NeuralFlowChart";
import { EMOTION_THEME, deriveVector } from "../lib/emotionTheme";

interface Props {
  state: StressState;
  onToggleMonitoring: () => void;
  onPlayMusic: () => void;
  onSwitchToSanctuary: () => void;
}

/**
 * DashboardView — the "Emotion Lab" instrument-panel design.
 * Sidebar navigation, multi-card grid, derived metrics, and a
 * glowing Neural Flow chart. All numbers come from the real
 * model output — see deriveVector() for how Focus/Stress/Fatigue
 * are computed from the probability distribution.
 */
export default function DashboardView({
  state,
  onToggleMonitoring,
  onPlayMusic,
  onSwitchToSanctuary,
}: Props) {
  const [activeNav, setActiveNav] = useState("sanctuary");
  const theme = EMOTION_THEME[state.emotion];
  const vector = deriveVector(state.proba, state.confidence);

  return (
    <div className="flex min-h-screen w-full bg-[#070b09] font-sora">
      <Sidebar
        active={activeNav}
        onSelect={setActiveNav}
        accent={theme.glow}
        onSwitchToSanctuary={onSwitchToSanctuary}
      />

      <main className="flex-1 overflow-y-auto px-8 pb-7 pt-20">
        {/* Top status row */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`h-[6px] w-[6px] rounded-full ${
                state.connected ? "bg-emerald-400" : "bg-white/25"
              }`}
            />
            <span className="font-sora text-[11px] text-white/40">
              {state.connected ? "Live" : "Reconnecting…"} · {state.keystrokes} keystrokes
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.open("http://localhost:8000/api/report?days=7", "_blank")}
              className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 font-sora text-[11px] font-medium text-white/70 transition-colors hover:bg-white/[0.10] hover:text-white"
            >
              <FileText className="h-3 w-3" />
              Weekly report
            </button>
            <button
              onClick={onToggleMonitoring}
              className="rounded-full px-4 py-1.5 font-sora text-[11px] font-semibold transition-colors"
              style={{
                backgroundColor: state.monitoringActive ? "rgba(255,255,255,0.06)" : theme.glow,
                color: state.monitoringActive ? "rgba(255,255,255,0.6)" : "#0a0f0d",
              }}
            >
              {state.monitoringActive ? "Pause monitoring" : "Initiate Calm"}
            </button>
          </div>
        </div>

        {/* Main grid: state card + vector panel */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-[minmax(0,1fr)_320px]">
          <DashboardStateCard
            emotion={state.emotion}
            confidence={state.confidence}
            music={state.music}
            onPlay={onPlayMusic}
          />

          <div className="flex min-w-0 flex-col gap-5">
            <VectorPanel focus={vector.focus} stress={vector.stress} fatigue={vector.fatigue} />
            <RecoveryStatsCard accent={theme.glow} />
            <DashboardMoodStream history={state.history} />
          </div>
        </div>

        {/* Neural flow chart, full width */}
        <div className="mt-5">
          <NeuralFlowChart history={state.history} currentEmotion={state.emotion} />
        </div>
      </main>
    </div>
  );
}
