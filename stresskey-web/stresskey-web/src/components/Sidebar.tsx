import { Sprout, Footprints, Activity, History, Sparkles, LayoutPanelLeft } from "lucide-react";
import { motion } from "framer-motion";

interface NavItem {
  key: string;
  label: string;
  icon: typeof Sprout;
}

const NAV_ITEMS: NavItem[] = [
  { key: "sanctuary", label: "Sanctuary", icon: Sprout },
  { key: "moodlab",   label: "Mood Lab",  icon: Footprints },
  { key: "biosonic",  label: "Bio-Sonic", icon: Activity },
  { key: "history",   label: "History",   icon: History },
  { key: "rituals",   label: "Rituals",   icon: Sparkles },
];

interface Props {
  active: string;
  onSelect: (key: string) => void;
  accent: string;
  onSwitchToSanctuary: () => void;
}

export default function Sidebar({ active, onSelect, accent, onSwitchToSanctuary }: Props) {
  return (
    <aside className="flex h-full w-[200px] shrink-0 flex-col border-r border-white/[0.06] bg-[#0a0f0d] px-4 py-6">
      <div className="mb-8 flex items-center gap-2.5 px-1">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: `${accent}22`, color: accent }}
        >
          <Sprout className="h-4 w-4" />
        </div>
        <div>
          <p className="font-sora text-[13px] font-semibold leading-tight" style={{ color: accent }}>
            Emotion Lab
          </p>
          <p className="font-sora text-[9px] leading-tight text-white/35">
            Biological Sanctuary
          </p>
        </div>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = active === item.key;
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              onClick={() => onSelect(item.key)}
              className="relative flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors"
              style={{
                backgroundColor: isActive ? `${accent}14` : "transparent",
                color: isActive ? accent : "rgba(255,255,255,0.45)",
              }}
            >
              {isActive && (
                <motion.span
                  layoutId="sidebar-active-bar"
                  className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-full"
                  style={{ backgroundColor: accent, boxShadow: `0 0 8px ${accent}` }}
                />
              )}
              <Icon className="h-3.5 w-3.5" />
              <span className="font-sora text-[12.5px] font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto">
        <button
          onClick={onSwitchToSanctuary}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-white/35
                     transition-colors hover:bg-white/[0.05] hover:text-white/70"
        >
          <LayoutPanelLeft className="h-3.5 w-3.5" />
          <span className="font-sora text-[11px] font-medium">Minimal mode</span>
        </button>
      </div>
    </aside>
  );
}
