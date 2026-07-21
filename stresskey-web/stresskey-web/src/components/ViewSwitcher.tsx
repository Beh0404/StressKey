import { Sparkles, LayoutGrid } from "lucide-react";

type ViewMode = "sanctuary" | "dashboard";

interface Props {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export default function ViewSwitcher({ mode, onChange }: Props) {
  return (
    <div
      className="fixed right-5 top-5 z-50 flex items-center gap-0.5 rounded-full
                 border border-white/10 bg-black/40 p-1 backdrop-blur-xl"
    >
      <button
        onClick={() => onChange("sanctuary")}
        className="flex items-center gap-1.5 rounded-full px-3 py-1.5 font-sora text-[11px] font-medium transition-colors"
        style={{
          backgroundColor: mode === "sanctuary" ? "rgba(255,255,255,0.12)" : "transparent",
          color: mode === "sanctuary" ? "white" : "rgba(255,255,255,0.4)",
        }}
        aria-pressed={mode === "sanctuary"}
      >
        <Sparkles className="h-3 w-3" />
        Sanctuary
      </button>
      <button
        onClick={() => onChange("dashboard")}
        className="flex items-center gap-1.5 rounded-full px-3 py-1.5 font-sora text-[11px] font-medium transition-colors"
        style={{
          backgroundColor: mode === "dashboard" ? "rgba(255,255,255,0.12)" : "transparent",
          color: mode === "dashboard" ? "white" : "rgba(255,255,255,0.4)",
        }}
        aria-pressed={mode === "dashboard"}
      >
        <LayoutGrid className="h-3 w-3" />
        Dashboard
      </button>
    </div>
  );
}
