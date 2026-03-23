const STATUS_COLORS: Record<string, string> = {
  // Claims
  draft: "bg-gray-500/20 text-gray-300 border-gray-500/30",
  ready: "bg-cyan/10 text-cyan border-cyan/30",
  submitted: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  accepted: "bg-lime/10 text-lime border-lime/30",
  denied: "bg-red-500/15 text-red-400 border-red-500/30",
  paid: "bg-lime/10 text-lime border-lime/30",
  // Denials
  appealed: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  overturned: "bg-lime/10 text-lime border-lime/30",
  upheld: "bg-red-500/15 text-red-400 border-red-500/30",
  // Encounters
  parsed: "bg-cyan/10 text-cyan border-cyan/30",
  coded: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  approved: "bg-lime/10 text-lime border-lime/30",
  // Risk
  low: "bg-lime/10 text-lime border-lime/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  high: "bg-red-500/15 text-red-400 border-red-500/30",
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors =
    STATUS_COLORS[status] ?? "bg-gray-500/20 text-gray-400 border-gray-500/30";
  return (
    <span
      className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-heading font-semibold border ${colors}`}
    >
      {status}
    </span>
  );
}
