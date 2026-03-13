import { useEffect, useState } from "react";
import { listDenials, generateAppeal } from "../api/client";
import type { Denial, AppealDocument } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function Denials() {
  const [denials, setDenials] = useState<Denial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appealResult, setAppealResult] = useState<AppealDocument | null>(null);
  const [appealingId, setAppealingId] = useState<string | null>(null);

  useEffect(() => {
    loadDenials();
  }, []);

  async function loadDenials() {
    try {
      setLoading(true);
      const data = await listDenials();
      setDenials(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load denials");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateAppeal(denialId: string) {
    try {
      setAppealingId(denialId);
      const appeal = await generateAppeal(denialId, {
        clinical_notes: "Patient required treatment as documented.",
        state: "CA",
      });
      setAppealResult(appeal);
      await loadDenials();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate appeal",
      );
    } finally {
      setAppealingId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Denials</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Appeal result */}
      {appealResult && (
        <div className="mb-4 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Generated Appeal</h3>
            <button
              onClick={() => setAppealResult(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-auto">
            {appealResult.appeal_text}
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : denials.length === 0 ? (
        <p className="text-gray-500">No denials found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Reason
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Amount
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {denials.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {d.payer_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {d.denial_reason_description}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {d.denied_amount ? `$${d.denied_amount.toFixed(2)}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {d.status === "denied" && (
                      <button
                        onClick={() => handleGenerateAppeal(d.id)}
                        disabled={appealingId === d.id}
                        className="text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                      >
                        {appealingId === d.id ? "Generating..." : "Generate Appeal"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
