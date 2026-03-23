export interface PerioData {
  readings: Record<string, number[]>; // tooth number -> [buccal, lingual, mesial] (3-point simplified)
  bleeding: Record<string, boolean[]>; // tooth number -> [buccal, lingual, mesial]
}

export const DEFAULT_PERIO: PerioData = {
  readings: {},
  bleeding: {},
};

interface PerioChartProps {
  data: PerioData;
  onChange: (data: PerioData) => void;
  missingTeeth?: Record<string, string>;
}

const UPPER_TEETH = Array.from({ length: 16 }, (_, i) => i + 1);
const LOWER_TEETH = Array.from({ length: 16 }, (_, i) => i + 17);
const SITES = ["B", "L", "M"]; // Buccal, Lingual, Mesial
const SITE_LABELS = ["Buc", "Lin", "Mes"];

function depthColor(depth: number): string {
  if (depth <= 0) return "text-gray-600";
  if (depth <= 3) return "text-green-400";
  if (depth <= 5) return "text-amber-400";
  return "text-red-400";
}

function depthBorder(depth: number): string {
  if (depth <= 0) return "border-gray-600/30";
  if (depth <= 3) return "border-green-400/30";
  if (depth <= 5) return "border-amber-400/30";
  return "border-red-400/30";
}

export default function PerioChart({
  data,
  onChange,
  missingTeeth = {},
}: PerioChartProps) {
  function getReadings(tooth: number): number[] {
    return data.readings[String(tooth)] || [0, 0, 0];
  }

  function setReading(tooth: number, siteIdx: number, value: number) {
    const key = String(tooth);
    const current = [...(data.readings[key] || [0, 0, 0])];
    current[siteIdx] = value;
    onChange({
      ...data,
      readings: { ...data.readings, [key]: current },
    });
  }

  function isMissing(tooth: number): boolean {
    return String(tooth) in missingTeeth;
  }

  function renderArch(teeth: number[], label: string) {
    return (
      <div>
        <p className="text-[10px] font-heading text-gray-500 uppercase tracking-wider mb-2">
          {label}
        </p>
        <div className="overflow-x-auto">
          <div className="inline-flex gap-px">
            {/* Site labels column */}
            <div className="flex flex-col items-end justify-end gap-px mr-1 pb-px">
              <div className="h-5 flex items-center">
                <span className="text-[9px] text-gray-600 font-heading">#</span>
              </div>
              {SITE_LABELS.map((sl) => (
                <div key={sl} className="h-7 flex items-center">
                  <span className="text-[9px] text-gray-600 font-heading">
                    {sl}
                  </span>
                </div>
              ))}
            </div>

            {/* Tooth columns */}
            {teeth.map((num) => {
              const missing = isMissing(num);
              const readings = getReadings(num);
              return (
                <div
                  key={num}
                  className={`flex flex-col items-center gap-px ${
                    missing ? "opacity-30" : ""
                  }`}
                >
                  {/* Tooth number */}
                  <div className="h-5 flex items-center justify-center w-10">
                    <span
                      className={`text-[10px] font-heading font-semibold ${
                        missing ? "text-gray-600 line-through" : "text-gray-400"
                      }`}
                    >
                      {num}
                    </span>
                  </div>

                  {/* 3 site inputs */}
                  {SITES.map((_, siteIdx) => {
                    const val = readings[siteIdx];
                    return (
                      <input
                        key={siteIdx}
                        type="number"
                        min={0}
                        max={15}
                        value={val || ""}
                        disabled={missing}
                        onChange={(e) => {
                          const v = parseInt(e.target.value) || 0;
                          setReading(num, siteIdx, Math.min(15, Math.max(0, v)));
                        }}
                        className={`w-10 h-7 rounded text-center text-xs font-body border bg-navy-900 focus:outline-none focus:ring-1 focus:ring-cyan/30 ${depthColor(val)} ${depthBorder(val)} ${
                          missing
                            ? "cursor-not-allowed bg-gray-800/20"
                            : "hover:border-gray-500/50"
                        }`}
                        style={{ MozAppearance: "textfield" }}
                      />
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {renderArch(UPPER_TEETH, "Upper Arch (Maxillary)")}
      <div className="border-t border-white/[0.06]" />
      {renderArch(LOWER_TEETH, "Lower Arch (Mandibular)")}

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-400" />
          <span className="text-[10px] text-gray-500 font-body">1-3mm</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-amber-400" />
          <span className="text-[10px] text-gray-500 font-body">4-5mm</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-400" />
          <span className="text-[10px] text-gray-500 font-body">6+mm</span>
        </div>
      </div>
    </div>
  );
}
