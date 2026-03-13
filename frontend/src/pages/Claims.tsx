import { useEffect, useState } from "react";
import { listClaims, submitClaim, assessRisk } from "../api/client";
import type { Claim, RiskAssessment } from "../api/types";
import StatusBadge from "../components/StatusBadge";

const STATUS_FILTERS = ["all", "draft", "ready", "submitted", "accepted", "denied", "paid"];

export default function Claims() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [riskResult, setRiskResult] = useState<{
    claimId: string;
    assessment: RiskAssessment;
  } | null>(null);

  useEffect(() => {
    loadClaims();
  }, [filter]);

  async function loadClaims() {
    try {
      setLoading(true);
      const data = await listClaims(filter === "all" ? undefined : filter);
      setClaims(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(claimId: string) {
    try {
      await submitClaim(claimId);
      await loadClaims();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit claim");
    }
  }

  async function handleAssessRisk(claimId: string) {
    try {
      const assessment = await assessRisk(claimId);
      setRiskResult({ claimId, assessment });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assess risk");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Claims</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-2 text-sm capitalize transition-colors ${
              filter === s
                ? "border-b-2 border-blue-600 text-blue-600 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Risk assessment result */}
      {riskResult && (
        <div className="mb-4 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Risk Assessment</h3>
            <button
              onClick={() => setRiskResult(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span>
              Score: <strong>{riskResult.assessment.risk_score}</strong>
            </span>
            <StatusBadge status={riskResult.assessment.risk_level} />
          </div>
          {riskResult.assessment.risk_factors.length > 0 && (
            <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
              {riskResult.assessment.risk_factors.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : claims.length === 0 ? (
        <p className="text-gray-500">No claims found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Provider
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payer
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
              {claims.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {c.provider_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.date_of_service}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.primary_payer_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.total_fee_submitted
                      ? `$${c.total_fee_submitted.toFixed(2)}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex gap-2">
                      {c.status === "draft" && (
                        <button
                          onClick={() => handleSubmit(c.id)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          Submit
                        </button>
                      )}
                      <button
                        onClick={() => handleAssessRisk(c.id)}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        Risk
                      </button>
                    </div>
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
