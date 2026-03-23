import { useState } from "react";

interface ToothChartProps {
  missingTeeth: Record<string, string>; // tooth number -> extraction date (or empty string)
  onChange: (missingTeeth: Record<string, string>) => void;
  compact?: boolean;
}

const UPPER_TEETH = Array.from({ length: 16 }, (_, i) => i + 1);
const LOWER_TEETH = Array.from({ length: 16 }, (_, i) => i + 17);

export default function ToothChart({
  missingTeeth,
  onChange,
  compact = false,
}: ToothChartProps) {
  const [showDateFor, setShowDateFor] = useState<string | null>(null);

  function toggleTooth(num: number) {
    const key = String(num);
    const next = { ...missingTeeth };
    if (next[key] !== undefined) {
      delete next[key];
      if (showDateFor === key) setShowDateFor(null);
    } else {
      next[key] = "";
      setShowDateFor(key);
    }
    onChange(next);
  }

  function setDate(num: number, date: string) {
    const key = String(num);
    onChange({ ...missingTeeth, [key]: date });
  }

  const isMissing = (num: number) => String(num) in missingTeeth;

  const boxSize = compact ? "w-7 h-7 text-[10px]" : "w-9 h-9 text-xs";

  function renderTooth(num: number) {
    const key = String(num);
    const missing = isMissing(num);
    return (
      <div key={num} className="flex flex-col items-center gap-1">
        <button
          type="button"
          onClick={() => toggleTooth(num)}
          className={`${boxSize} rounded flex items-center justify-center font-heading font-semibold border transition-colors relative ${
            missing
              ? "bg-red-500/15 border-red-500/40 text-red-400/60"
              : "bg-navy-900 border-gray-600/40 text-gray-400 hover:border-cyan/40 hover:text-gray-200"
          }`}
          title={missing ? `Tooth #${num} — missing (click to restore)` : `Tooth #${num} (click to mark missing)`}
        >
          {num}
          {missing && (
            <span className="absolute inset-0 flex items-center justify-center text-red-400/80 text-lg font-bold pointer-events-none">
              &times;
            </span>
          )}
        </button>
        {missing && showDateFor === key && !compact && (
          <input
            type="date"
            value={missingTeeth[key] || ""}
            onChange={(e) => setDate(num, e.target.value)}
            className="input-field !p-0.5 !text-[10px] w-[90px] text-center"
            placeholder="Date"
            title="Extraction date"
          />
        )}
        {missing && missingTeeth[key] && showDateFor !== key && !compact && (
          <button
            type="button"
            onClick={() => setShowDateFor(key)}
            className="text-[9px] text-gray-600 hover:text-gray-400 transition-colors"
          >
            {missingTeeth[key]}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Upper arch */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-1.5">
          Upper Arch (Maxillary)
        </p>
        <div className="flex flex-wrap gap-1">
          {UPPER_TEETH.map(renderTooth)}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-white/[0.06]" />

      {/* Lower arch */}
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-1.5">
          Lower Arch (Mandibular)
        </p>
        <div className="flex flex-wrap gap-1">
          {LOWER_TEETH.map(renderTooth)}
        </div>
      </div>

      {/* Legend */}
      {!compact && (
        <div className="flex items-center gap-4 pt-1">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded border border-gray-600/40 bg-navy-900" />
            <span className="text-[10px] text-gray-500 font-body">Present</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded border border-red-500/40 bg-red-500/15 flex items-center justify-center text-red-400/80 text-[8px] font-bold">
              &times;
            </div>
            <span className="text-[10px] text-gray-500 font-body">Missing</span>
          </div>
          <span className="text-[10px] text-gray-600 font-body">
            Click a tooth to toggle
          </span>
        </div>
      )}
    </div>
  );
}
