import { motion } from "framer-motion";

interface VectorRow {
  label: string;
  value: number;
  color: string;
}

interface Props {
  focus: number;
  stress: number;
  fatigue: number;
}

export default function VectorPanel({ focus, stress, fatigue }: Props) {
  const rows: VectorRow[] = [
    { label: "Focus",   value: focus,   color: "#34e7b8" },
    { label: "Stress",  value: stress,  color: "#ff5c7a" },
    { label: "Fatigue", value: fatigue, color: "#5b8cff" },
  ];

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0d1411] p-5">
      <p className="mb-5 font-sora text-[13px] font-semibold text-white/85">
        Current Vector
      </p>

      <div className="flex flex-col gap-4">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="font-sora text-[11.5px] text-white/55">{row.label}</span>
              <span
                className="font-sora text-[11.5px] font-semibold tabular-nums"
                style={{ color: row.color }}
              >
                {row.value}%
              </span>
            </div>
            <div className="h-[5px] w-full overflow-hidden rounded-full bg-white/[0.06]">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: row.color }}
                initial={{ width: 0 }}
                animate={{ width: `${row.value}%` }}
                transition={{ duration: 0.7, ease: "easeOut" }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
