import { useEffect, useState } from "react";
import { useStressSocket } from "./hooks/useStressSocket";
import SanctuaryView from "./views/SanctuaryView";
import DashboardView from "./views/DashboardView";
import ViewSwitcher from "./components/ViewSwitcher";

type ViewMode = "sanctuary" | "dashboard";
const STORAGE_KEY = "stresskey:view-mode";

function App() {
  const { state, startMonitoring, stopMonitoring, playMusic, refreshMusic } =
    useStressSocket();

  const [mode, setMode] = useState<ViewMode>(() => {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    return saved === "dashboard" ? "dashboard" : "sanctuary";
  });

  useEffect(() => {
    window.sessionStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  function handleToggleMonitoring() {
    if (state.monitoringActive) stopMonitoring();
    else startMonitoring();
  }

  return (
    <div className="relative">
      <ViewSwitcher mode={mode} onChange={setMode} />

      {mode === "sanctuary" ? (
        <SanctuaryView
          state={state}
          onToggleMonitoring={handleToggleMonitoring}
          onPlayMusic={playMusic}
          onRefreshMusic={refreshMusic}
        />
      ) : (
        <DashboardView
          state={state}
          onToggleMonitoring={handleToggleMonitoring}
          onPlayMusic={playMusic}
          onSwitchToSanctuary={() => setMode("sanctuary")}
        />
      )}
    </div>
  );
}

export default App;
