const STATUS_COLORS: Record<string, string> = {
  // Claims
  draft: "bg-gray-100 text-gray-700",
  ready: "bg-blue-100 text-blue-700",
  submitted: "bg-yellow-100 text-yellow-700",
  accepted: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
  paid: "bg-green-100 text-green-700",
  // Denials
  appealed: "bg-purple-100 text-purple-700",
  overturned: "bg-green-100 text-green-700",
  upheld: "bg-red-100 text-red-700",
  // Encounters
  parsed: "bg-blue-100 text-blue-700",
  coded: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors}`}
    >
      {status}
    </span>
  );
}
