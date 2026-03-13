import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPatients, listClaims, listDenials, health } from "../api/client";

interface Stats {
  patients: number;
  claims: number;
  denials: number;
  healthy: boolean;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [patients, claims, denials, h] = await Promise.all([
          listPatients().catch(() => []),
          listClaims().catch(() => []),
          listDenials().catch(() => []),
          health().catch(() => ({ status: "unhealthy" })),
        ]);
        setStats({
          patients: patients.length,
          claims: claims.length,
          denials: denials.length,
          healthy: h.status === "healthy",
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <p className="text-gray-500">Loading dashboard...</p>;
  }

  const cards = [
    {
      label: "Patients",
      count: stats?.patients ?? 0,
      link: "/patients",
      color: "bg-blue-50 text-blue-700",
    },
    {
      label: "Claims",
      count: stats?.claims ?? 0,
      link: "/claims",
      color: "bg-green-50 text-green-700",
    },
    {
      label: "Denials",
      count: stats?.denials ?? 0,
      link: "/denials",
      color: "bg-red-50 text-red-700",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* API health indicator */}
      <div className="mb-6 flex items-center gap-2 text-sm">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            stats?.healthy ? "bg-green-500" : "bg-red-500"
          }`}
        />
        <span className="text-gray-500">
          API: {stats?.healthy ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((card) => (
          <Link
            key={card.label}
            to={card.link}
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
          >
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className={`text-3xl font-bold mt-1 ${card.color}`}>
              {card.count}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
