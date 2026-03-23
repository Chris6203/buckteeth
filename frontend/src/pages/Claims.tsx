import { useEffect, useState, useMemo } from "react";
import { listClaims, submitClaim, assessRisk, listPatients } from "../api/client";
import type { Claim, Patient, RiskAssessment } from "../api/types";
import StatusBadge from "../components/StatusBadge";

const STATUS_FILTERS = [
  "all",
  "draft",
  "ready",
  "submitted",
  "accepted",
  "denied",
  "paid",
];

function formatError(msg: string): string {
  if (msg.includes("Internal Server Error")) {
    return "This feature requires a valid API key. Check Practice Setup.";
  }
  return msg;
}

function formatDollars(amount: number): string {
  return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function Claims() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [riskResult, setRiskResult] = useState<{
    claimId: string;
    assessment: RiskAssessment;
  } | null>(null);
  const [patientMap, setPatientMap] = useState<Record<string, string>>({});

  useEffect(() => {
    listPatients()
      .then((patients: Patient[]) => {
        const map: Record<string, string> = {};
        for (const p of patients) {
          map[p.id] = `${p.first_name} ${p.last_name}`;
        }
        setPatientMap(map);
      })
      .catch(() => {
        // Silently ignore — we'll fall back to truncated ID
      });
  }, []);

  useEffect(() => {
    loadClaims();
  }, [filter]);

  const totals = useMemo(() => {
    let total = 0;
    let accepted = 0;
    let denied = 0;
    let pending = 0;
    for (const c of claims) {
      const fee = c.total_fee_submitted ?? 0;
      total += fee;
      if (c.status === "accepted" || c.status === "paid") accepted += fee;
      else if (c.status === "denied") denied += fee;
      else pending += fee;
    }
    return { total, accepted, denied, pending };
  }, [claims]);

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

  function getPatientName(patientId: string): string {
    return patientMap[patientId] || patientId.slice(0, 8) + "...";
  }

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-heading font-bold text-gray-100">
          Claims
        </h1>
        <p className="text-sm font-body text-gray-500 mt-1">
          {loading
            ? "Track and manage insurance claims"
            : `${claims.length} claim${claims.length !== 1 ? "s" : ""}`}
        </p>
      </div>

      {error && (
        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-body">
          {formatError(error)}
        </div>
      )}

      {/* Summary totals bar */}
      {!loading && claims.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <div className="card p-4">
            <p className="text-xs font-body text-gray-500 uppercase tracking-wider">Total Value</p>
            <p className="text-lg font-heading font-bold text-gray-100 mt-1">{formatDollars(totals.total)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-body text-gray-500 uppercase tracking-wider">Accepted</p>
            <p className="text-lg font-heading font-bold mt-1" style={{ color: "#00FF88" }}>{formatDollars(totals.accepted)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-body text-gray-500 uppercase tracking-wider">Denied</p>
            <p className="text-lg font-heading font-bold text-red-400 mt-1">{formatDollars(totals.denied)}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-body text-gray-500 uppercase tracking-wider">Pending</p>
            <p className="text-lg font-heading font-bold mt-1" style={{ color: "#00D4FF" }}>{formatDollars(totals.pending)}</p>
          </div>
        </div>
      )}

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-5 border-b border-white/[0.06] overflow-x-auto">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-4 py-2.5 text-sm font-heading capitalize whitespace-nowrap transition-all duration-200 ${
              filter === s
                ? "border-b-2 border-cyan text-cyan font-semibold"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Risk assessment result */}
      {riskResult && (
        <div className="mb-5 card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading font-semibold text-gray-200">
              Risk Assessment
            </h3>
            <button
              onClick={() => setRiskResult(null)}
              className="text-gray-500 hover:text-gray-300 text-sm font-body transition-colors"
            >
              Dismiss
            </button>
          </div>
          <div className="flex items-center gap-4 text-sm font-body">
            <span className="text-gray-400">
              Score:{" "}
              <strong className="text-gray-100">
                {riskResult.assessment.risk_score}
              </strong>
            </span>
            <StatusBadge status={riskResult.assessment.risk_level} />
          </div>
          {riskResult.assessment.risk_factors.length > 0 && (
            <ul className="mt-3 text-sm text-gray-400 font-body space-y-1">
              {riskResult.assessment.risk_factors.map((f, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-cyan mt-1">&#x2022;</span>
                  {f}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
          <span className="font-body text-sm">Loading...</span>
        </div>
      ) : claims.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          <p className="text-gray-400 font-body">No claims found</p>
          <p className="text-gray-600 font-body text-sm mt-1">
            Claims will appear here once created from coded encounters
          </p>
        </div>
      ) : (
        <>
          {/* Desktop table layout */}
          <div className="card overflow-hidden hidden md:block">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="table-header">Patient</th>
                  <th className="table-header">Provider</th>
                  <th className="table-header">Date</th>
                  <th className="table-header">Payer</th>
                  <th className="table-header">Amount</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {claims.map((c) => (
                  <>
                    <tr
                      key={c.id}
                      onClick={() => toggleExpand(c.id)}
                      className="hover:bg-white/[0.02] transition-colors cursor-pointer"
                    >
                      <td className="table-cell text-gray-300">
                        {getPatientName(c.patient_id)}
                      </td>
                      <td className="table-cell font-medium text-gray-100">
                        {c.provider_name}
                      </td>
                      <td className="table-cell text-gray-400">
                        {c.date_of_service}
                      </td>
                      <td className="table-cell text-gray-400">
                        {c.primary_payer_name}
                      </td>
                      <td className="table-cell text-gray-400">
                        {c.total_fee_submitted
                          ? formatDollars(c.total_fee_submitted)
                          : "\u2014"}
                      </td>
                      <td className="table-cell">
                        <StatusBadge status={c.status} />
                      </td>
                      <td className="table-cell">
                        <div className="flex gap-3" onClick={(e) => e.stopPropagation()}>
                          {c.status === "draft" && (
                            <button
                              onClick={() => handleSubmit(c.id)}
                              className="text-cyan hover:text-cyan-400 font-medium text-sm transition-colors"
                            >
                              Submit
                            </button>
                          )}
                          <button
                            onClick={() => handleAssessRisk(c.id)}
                            className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
                          >
                            Risk
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedId === c.id && c.procedures.length > 0 && (
                      <tr key={`${c.id}-procedures`}>
                        <td colSpan={7} className="px-4 py-3 bg-navy-900/50">
                          <div className="text-xs font-heading font-semibold text-gray-500 uppercase tracking-wider mb-2">
                            Procedures
                          </div>
                          <div className="space-y-1">
                            {c.procedures.map((p) => (
                              <div
                                key={p.id}
                                className="flex items-center justify-between text-sm font-body py-1.5 px-3 rounded-lg bg-white/[0.02]"
                              >
                                <div className="flex items-center gap-3">
                                  <span className="font-mono text-cyan font-medium text-xs bg-cyan/10 px-2 py-0.5 rounded">
                                    {p.cdt_code}
                                  </span>
                                  <span className="text-gray-300">
                                    {p.cdt_description}
                                  </span>
                                </div>
                                <span className="text-gray-400 font-medium">
                                  {p.fee_submitted != null
                                    ? formatDollars(p.fee_submitted)
                                    : "\u2014"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card layout */}
          <div className="space-y-3 md:hidden">
            {claims.map((c) => (
              <div key={c.id} className="card p-4">
                <div
                  onClick={() => toggleExpand(c.id)}
                  className="cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-heading font-medium text-gray-100">
                      {c.provider_name}
                    </span>
                    <StatusBadge status={c.status} />
                  </div>
                  <div className="flex items-center justify-between text-sm font-body mb-1">
                    <span className="text-gray-400">{getPatientName(c.patient_id)}</span>
                    <span className="text-gray-300 font-medium">
                      {c.total_fee_submitted
                        ? formatDollars(c.total_fee_submitted)
                        : "\u2014"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-body text-gray-500">
                    <span>{c.date_of_service}</span>
                    <span>{c.primary_payer_name}</span>
                  </div>
                </div>

                {/* Expanded procedures */}
                {expandedId === c.id && c.procedures.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/[0.06] space-y-1.5">
                    <div className="text-xs font-heading font-semibold text-gray-500 uppercase tracking-wider">
                      Procedures
                    </div>
                    {c.procedures.map((p) => (
                      <div key={p.id} className="flex items-center justify-between text-sm font-body py-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-cyan text-xs bg-cyan/10 px-1.5 py-0.5 rounded shrink-0">
                            {p.cdt_code}
                          </span>
                          <span className="text-gray-400 truncate">{p.cdt_description}</span>
                        </div>
                        <span className="text-gray-300 font-medium shrink-0 ml-2">
                          {p.fee_submitted != null ? formatDollars(p.fee_submitted) : "\u2014"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action buttons */}
                <div className="mt-3 pt-3 border-t border-white/[0.06] flex gap-3">
                  {c.status === "draft" && (
                    <button
                      onClick={() => handleSubmit(c.id)}
                      className="text-cyan hover:text-cyan-400 font-medium text-sm transition-colors"
                    >
                      Submit
                    </button>
                  )}
                  <button
                    onClick={() => handleAssessRisk(c.id)}
                    className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
                  >
                    Risk
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
