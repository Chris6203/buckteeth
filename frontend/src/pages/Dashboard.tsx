import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPatients, listClaims, listDenials, health } from "../api/client";
import type { Claim, Denial } from "../api/types";

interface Stats {
  patients: number;
  claimsTotal: number;
  claimsDollar: number;
  denialsCount: number;
  denialsDollar: number;
  healthy: boolean;
  recentClaims: Claim[];
}

function formatDollar(cents: number): string {
  if (cents >= 100_000) return `$${Math.round(cents / 1000)}k`;
  return `$${cents.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(() => {
    // Open by default if practice setup is incomplete
    try {
      const data = JSON.parse(localStorage.getItem("pp_practice_setup") || "{}");
      const practice = data.practice || {};
      return !(practice.practice_name && practice.npi && practice.tax_id);
    } catch { return true; }
  });

  useEffect(() => {
    async function load() {
      try {
        const [patients, claims, denials, h] = await Promise.all([
          listPatients().catch(() => []),
          listClaims().catch(() => [] as Claim[]),
          listDenials().catch(() => [] as Denial[]),
          health().catch(() => ({ status: "unhealthy" })),
        ]);

        const claimsDollar = claims.reduce(
          (sum: number, c: Claim) => sum + (c.total_fee_submitted ?? 0),
          0,
        );
        const denialsDollar = denials.reduce(
          (sum: number, d: Denial) => sum + (d.denied_amount ?? 0),
          0,
        );

        // Sort claims by created_at descending and take the most recent 4
        const sorted = [...claims].sort((a, b) =>
          (b.created_at ?? "").localeCompare(a.created_at ?? ""),
        );

        setStats({
          patients: patients.length,
          claimsTotal: claims.length,
          claimsDollar,
          denialsCount: denials.length,
          denialsDollar,
          healthy: (h as { status: string }).status === "healthy",
          recentClaims: sorted.slice(0, 4),
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-3 text-gray-400">
        <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
        <span className="font-body text-sm">Loading dashboard...</span>
      </div>
    );
  }

  const cards = [
    {
      label: "Patients",
      display: `${stats?.patients ?? 0}`,
      sub: null as string | null,
      link: "/patients",
      icon: (
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
        </svg>
      ),
      accent: "text-cyan",
    },
    {
      label: "Claims",
      display: formatDollar(stats?.claimsDollar ?? 0),
      sub: `${stats?.claimsTotal ?? 0} total`,
      link: "/claims",
      icon: (
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      ),
      accent: "text-lime",
    },
    {
      label: "Denials",
      display: formatDollar(stats?.denialsDollar ?? 0),
      sub: `${stats?.denialsCount ?? 0} at risk`,
      link: "/denials",
      icon: (
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      ),
      accent: "text-red-400",
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-heading font-bold text-gray-100">
            Dashboard
          </h1>
          <p className="text-sm font-body text-gray-500 mt-1">
            AI-powered dental insurance coding
          </p>
        </div>
        <div className="flex items-center gap-2.5 card px-4 py-2.5">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${
              stats?.healthy ? "bg-lime animate-pulse" : "bg-red-500"
            }`}
          />
          <span className="text-sm font-body text-gray-400">
            API {stats?.healthy ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
        {cards.map((card) => (
          <Link
            key={card.label}
            to={card.link}
            className="card-hover group p-6"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-body text-gray-400 mb-1">
                  {card.label}
                </p>
                <p className={`text-4xl font-heading font-bold ${card.accent}`}>
                  {card.display}
                </p>
                {card.sub && (
                  <p className="text-xs font-body text-gray-500 mt-1">
                    {card.sub}
                  </p>
                )}
              </div>
              <div className={`${card.accent} opacity-30 group-hover:opacity-60 transition-opacity`}>
                {card.icon}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Recent Activity */}
      {stats && stats.recentClaims.length > 0 && (
        <div className="card p-6 mb-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-heading font-bold text-gray-100">
              Recent Activity
            </h2>
            <Link
              to="/claims"
              className="text-xs font-heading font-semibold text-cyan hover:text-cyan-400 transition-colors"
            >
              View all claims
            </Link>
          </div>
          <div className="space-y-2">
            {stats.recentClaims.map((claim) => {
              const statusColor =
                claim.status === "accepted" || claim.status === "paid"
                  ? "bg-lime/10 text-lime border-lime/30"
                  : claim.status === "denied"
                    ? "bg-red-500/10 text-red-400 border-red-500/30"
                    : claim.status === "submitted"
                      ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
                      : "bg-white/[0.06] text-gray-400 border-white/[0.08]";

              return (
                <Link
                  key={claim.id}
                  to={`/claims`}
                  className="flex items-center justify-between bg-navy-900 rounded-lg p-3 border border-white/[0.04] hover:border-white/[0.08] transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`text-xs font-heading font-semibold px-2 py-0.5 rounded-md border shrink-0 ${statusColor}`}
                    >
                      {claim.status}
                    </span>
                    <span className="text-sm font-body text-gray-300 truncate">
                      {claim.primary_payer_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="text-sm font-heading font-semibold text-gray-200">
                      {claim.total_fee_submitted != null
                        ? `$${claim.total_fee_submitted.toLocaleString()}`
                        : "--"}
                    </span>
                    <span className="text-xs font-body text-gray-600">
                      {claim.date_of_service}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* How it works */}
      <div className="card p-6 mb-5">
        <h2 className="text-lg font-heading font-bold text-gray-100 mb-4">
          How Phenomenal Problems Works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              step: "1",
              title: "Dictate or Type",
              desc: "After seeing a patient, dictate your clinical notes or type them in. Attach X-rays or intraoral photos.",
              color: "text-cyan border-cyan/30 bg-cyan/10",
            },
            {
              step: "2",
              title: "AI Codes It",
              desc: "AI parses your notes, identifies procedures, and suggests the correct CDT codes with confidence scores.",
              color: "text-purple-400 border-purple-500/30 bg-purple-500/10",
            },
            {
              step: "3",
              title: "Validation",
              desc: "Checks for missing documentation, frequency violations, preauth requirements, and known denial patterns.",
              color: "text-amber-400 border-amber-500/30 bg-amber-500/10",
            },
            {
              step: "4",
              title: "Claim Generated",
              desc: "Approve the codes and a complete insurance claim is created with proper narratives and documentation.",
              color: "text-lime border-lime/30 bg-lime/10",
            },
          ].map((item) => (
            <div key={item.step} className="relative">
              <div
                className={`w-8 h-8 rounded-lg ${item.color} border flex items-center justify-center text-sm font-heading font-bold mb-3`}
              >
                {item.step}
              </div>
              <h3 className="text-sm font-heading font-semibold text-gray-200 mb-1">
                {item.title}
              </h3>
              <p className="text-xs font-body text-gray-500 leading-relaxed">
                {item.desc}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-5 pt-4 border-t border-white/[0.06]">
          <Link
            to="/encounters"
            className="btn-primary inline-flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
            </svg>
            Start New Encounter
          </Link>
        </div>
      </div>

      {/* What it catches */}
      <div className="card p-6 mb-5">
        <h2 className="text-lg font-heading font-bold text-gray-100 mb-4">
          What the AI Catches
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                </svg>
              ),
              title: "Missing X-rays",
              desc: "Flags when procedures require radiographic evidence that hasn't been attached",
              color: "text-red-400",
            },
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
              ),
              title: "Frequency violations",
              desc: "Checks payer-specific limits (e.g., prophy 2x/year, crown 1x/5 years per tooth)",
              color: "text-amber-400",
            },
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
                </svg>
              ),
              title: "Pre-auth requirements",
              desc: "Warns when a procedure needs pre-authorization from the patient's insurance",
              color: "text-purple-400",
            },
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                </svg>
              ),
              title: "Image verification",
              desc: "Claude Vision checks that X-rays actually support the procedures being billed",
              color: "text-cyan",
            },
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
                </svg>
              ),
              title: "Denial patterns",
              desc: "Learns from prior denials — if a payer denied this code before, you'll know before submitting",
              color: "text-lime",
            },
            {
              icon: (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                </svg>
              ),
              title: "Bundling issues",
              desc: "Detects procedure combinations that payers commonly reject or bundle together",
              color: "text-gray-400",
            },
          ].map((item, i) => (
            <div
              key={i}
              className="flex items-start gap-3 bg-navy-900 rounded-lg p-3 border border-white/[0.04]"
            >
              <div className={`${item.color} mt-0.5 shrink-0`}>{item.icon}</div>
              <div>
                <p className="text-sm font-heading font-semibold text-gray-200">
                  {item.title}
                </p>
                <p className="text-xs font-body text-gray-500 mt-0.5 leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Setup checklist */}
      <div className="card p-6">
        <button
          onClick={() => setShowSetup(!showSetup)}
          className="w-full flex items-center justify-between"
        >
          <h2 className="text-lg font-heading font-bold text-gray-100">
            Practice Setup Checklist
          </h2>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${showSetup ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        </button>

        {showSetup && (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-gray-400 font-body">
              To get the most out of Phenomenal Problems, your practice will need
              to provide the following information. The system works out of the
              box for AI coding, but these items unlock full claim submission and
              denial prevention.
            </p>

            {[
              {
                title: "Provider Information",
                status: "required",
                items: [
                  "Provider name(s) and credentials (DDS, DMD, RDH)",
                  "NPI number (National Provider Identifier) — required for all claim submissions",
                  "Tax ID / EIN — required for claim billing",
                  "Practice address and phone number",
                  "Taxonomy code (1223G0001X for general dentistry)",
                ],
              },
              {
                title: "Patient Insurance Details",
                status: "required",
                items: [
                  "Insurance company name and payer ID (we support 26+ major dental payers)",
                  "Subscriber ID / member number",
                  "Group number",
                  "Patient relationship to subscriber (self, spouse, child)",
                  "Primary and secondary insurance (if applicable)",
                ],
              },
              {
                title: "Fee Schedule",
                status: "recommended",
                items: [
                  "Your practice's UCR (usual, customary, and reasonable) fees per CDT code",
                  "Contracted rates per payer (if in-network)",
                  "This allows us to calculate accurate claim amounts and estimate patient responsibility",
                ],
              },
              {
                title: "Clearinghouse Account",
                status: "for_live_submission",
                items: [
                  "Claim.MD, DentalXChange, Availity, or another clearinghouse account",
                  "Account ID and API credentials",
                  "Most practices already have this — it's how you submit claims electronically today",
                  "Not needed for AI coding and validation — only for actual claim submission",
                ],
              },
              {
                title: "Practice Management System (Optional)",
                status: "optional",
                items: [
                  "Open Dental, Dentrix, Eaglesoft, or other PMS",
                  "Connection credentials for auto-importing patients and encounters",
                  "Not required — you can enter patients manually or use the system standalone",
                ],
              },
              {
                title: "Historical Data (Optional but Valuable)",
                status: "optional",
                items: [
                  "Prior denial records — so the AI can learn your specific payer patterns",
                  "Patient treatment history — so frequency checks are accurate",
                  "Past claims data — helps calibrate the denial risk engine",
                  "The more history you provide, the better the denial prevention becomes",
                ],
              },
            ].map((section, i) => (
              <div key={i} className="bg-navy-900 rounded-lg p-4 border border-white/[0.04]">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-sm font-heading font-semibold text-gray-200">
                    {section.title}
                  </h3>
                  <span
                    className={`text-xs font-heading font-semibold px-2 py-0.5 rounded-md border ${
                      section.status === "required"
                        ? "text-cyan border-cyan/30 bg-cyan/10"
                        : section.status === "recommended"
                          ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
                          : section.status === "for_live_submission"
                            ? "text-purple-400 border-purple-500/30 bg-purple-500/10"
                            : "text-gray-500 border-white/[0.08] bg-white/[0.03]"
                    }`}
                  >
                    {section.status === "required"
                      ? "Required"
                      : section.status === "recommended"
                        ? "Recommended"
                        : section.status === "for_live_submission"
                          ? "For Live Submission"
                          : "Optional"}
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {section.items.map((item, j) => (
                    <li
                      key={j}
                      className="flex items-start gap-2 text-xs font-body text-gray-400"
                    >
                      <span className="text-gray-600 mt-0.5 shrink-0">
                        &#x2022;
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            <div className="bg-cyan-50 border border-cyan/20 rounded-lg p-4">
              <p className="text-sm font-body text-gray-300">
                <strong className="text-cyan font-heading">
                  Works without any setup:
                </strong>{" "}
                AI clinical note parsing, CDT code suggestions, image analysis,
                documentation checks, and appeal letter generation all work
                immediately. The items above are needed to submit claims to real
                insurance companies and maximize denial prevention accuracy.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
