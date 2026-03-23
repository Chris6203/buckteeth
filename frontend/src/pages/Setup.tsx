import { useState, useEffect } from "react";
import { getSettings, updateSettings } from "../api/client";

interface PracticeInfo {
  practice_name: string;
  provider_name: string;
  provider_credentials: string;
  npi: string;
  tax_id: string;
  taxonomy_code: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip: string;
  phone: string;
  email: string;
}

interface ClearinghouseInfo {
  name: string;
  account_id: string;
  auth_key: string;
  environment: string;
}

interface FeeScheduleEntry {
  cdt_code: string;
  description: string;
  fee: string;
}

const STORAGE_KEY = "pp_practice_setup";

const DEFAULT_PRACTICE: PracticeInfo = {
  practice_name: "",
  provider_name: "",
  provider_credentials: "DDS",
  npi: "",
  tax_id: "",
  taxonomy_code: "1223G0001X",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  zip: "",
  phone: "",
  email: "",
};

const DEFAULT_CLEARINGHOUSE: ClearinghouseInfo = {
  name: "claim.md",
  account_id: "",
  auth_key: "",
  environment: "sandbox",
};

const COMMON_FEES: FeeScheduleEntry[] = [
  { cdt_code: "D0120", description: "Periodic oral evaluation", fee: "" },
  { cdt_code: "D0150", description: "Comprehensive oral evaluation", fee: "" },
  { cdt_code: "D0210", description: "Full mouth X-rays", fee: "" },
  { cdt_code: "D0220", description: "Periapical X-ray (first)", fee: "" },
  { cdt_code: "D0230", description: "Periapical X-ray (additional)", fee: "" },
  { cdt_code: "D0274", description: "Bitewings (four images)", fee: "" },
  { cdt_code: "D0330", description: "Panoramic X-ray", fee: "" },
  { cdt_code: "D1110", description: "Prophylaxis (adult)", fee: "" },
  { cdt_code: "D1120", description: "Prophylaxis (child)", fee: "" },
  { cdt_code: "D1206", description: "Fluoride varnish", fee: "" },
  { cdt_code: "D1351", description: "Sealant (per tooth)", fee: "" },
  { cdt_code: "D2140", description: "Amalgam — one surface", fee: "" },
  { cdt_code: "D2150", description: "Amalgam — two surfaces", fee: "" },
  { cdt_code: "D2160", description: "Amalgam — three surfaces", fee: "" },
  { cdt_code: "D2330", description: "Composite — one surface, anterior", fee: "" },
  { cdt_code: "D2331", description: "Composite — two surfaces, anterior", fee: "" },
  { cdt_code: "D2391", description: "Composite — one surface, posterior", fee: "" },
  { cdt_code: "D2392", description: "Composite — two surfaces, posterior", fee: "" },
  { cdt_code: "D2393", description: "Composite — three surfaces, posterior", fee: "" },
  { cdt_code: "D2740", description: "Crown — porcelain/ceramic", fee: "" },
  { cdt_code: "D2750", description: "Crown — porcelain fused to metal", fee: "" },
  { cdt_code: "D2950", description: "Core buildup", fee: "" },
  { cdt_code: "D3310", description: "Root canal — anterior", fee: "" },
  { cdt_code: "D3320", description: "Root canal — premolar", fee: "" },
  { cdt_code: "D3330", description: "Root canal — molar", fee: "" },
  { cdt_code: "D4341", description: "SRP — 4+ teeth per quadrant", fee: "" },
  { cdt_code: "D4342", description: "SRP — 1-3 teeth per quadrant", fee: "" },
  { cdt_code: "D4910", description: "Periodontal maintenance", fee: "" },
  { cdt_code: "D5110", description: "Complete denture — upper", fee: "" },
  { cdt_code: "D5120", description: "Complete denture — lower", fee: "" },
  { cdt_code: "D7140", description: "Extraction — erupted tooth", fee: "" },
  { cdt_code: "D7210", description: "Extraction — surgical", fee: "" },
  { cdt_code: "D7240", description: "Extraction — impacted (bony)", fee: "" },
];

const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
];

type Tab = "practice" | "fees" | "clearinghouse" | "status";

export default function Setup() {
  const [tab, setTab] = useState<Tab>("practice");
  const [practice, setPractice] = useState<PracticeInfo>(DEFAULT_PRACTICE);
  const [clearinghouse, setClearinghouse] = useState<ClearinghouseInfo>(DEFAULT_CLEARINGHOUSE);
  const [fees, setFees] = useState<FeeScheduleEntry[]>(COMMON_FEES);
  const [saved, setSaved] = useState(false);

  // Load from backend first, fall back to localStorage
  useEffect(() => {
    getSettings()
      .then((s) => {
        if (s.practice_name || s.npi) {
          setPractice({
            practice_name: s.practice_name,
            provider_name: s.provider_name,
            provider_credentials: s.provider_credentials || "DDS",
            npi: s.npi,
            tax_id: s.tax_id,
            taxonomy_code: s.taxonomy_code || "1223G0001X",
            address_line1: s.address_line1,
            address_line2: s.address_line2,
            city: s.city,
            state: s.state,
            zip: s.zip,
            phone: s.phone,
            email: s.email,
          });
          setClearinghouse({
            name: s.clearinghouse_name || "claim.md",
            account_id: s.clearinghouse_account_id,
            auth_key: "", // Don't load auth key from server for security
            environment: s.clearinghouse_environment || "sandbox",
          });
          if (s.fee_schedule && Object.keys(s.fee_schedule).length > 0) {
            setFees((prev) =>
              prev.map((f) => ({
                ...f,
                fee: s.fee_schedule[f.cdt_code]
                  ? String(s.fee_schedule[f.cdt_code])
                  : f.fee,
              })),
            );
          }
          return;
        }
        throw new Error("no server data");
      })
      .catch(() => {
        // Fall back to localStorage
        try {
          const data = localStorage.getItem(STORAGE_KEY);
          if (data) {
            const parsed = JSON.parse(data);
            if (parsed.practice) setPractice({ ...DEFAULT_PRACTICE, ...parsed.practice });
            if (parsed.clearinghouse) setClearinghouse({ ...DEFAULT_CLEARINGHOUSE, ...parsed.clearinghouse });
            if (parsed.fees) setFees(parsed.fees);
          }
        } catch {}
      });
  }, []);

  async function handleSave() {
    // Save to localStorage
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ practice, clearinghouse, fees }),
    );

    // Save to backend
    const feeSchedule: Record<string, number> = {};
    for (const f of fees) {
      if (f.fee && parseFloat(f.fee) > 0) {
        feeSchedule[f.cdt_code] = parseFloat(f.fee);
      }
    }

    try {
      await updateSettings({
        ...practice,
        clearinghouse_name: clearinghouse.name,
        clearinghouse_account_id: clearinghouse.account_id,
        clearinghouse_environment: clearinghouse.environment,
        fee_schedule: feeSchedule,
      });
    } catch {
      // Still saved to localStorage even if backend fails
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function updatePractice(field: keyof PracticeInfo, value: string) {
    setPractice((prev) => ({ ...prev, [field]: value }));
  }

  function updateClearinghouse(field: keyof ClearinghouseInfo, value: string) {
    setClearinghouse((prev) => ({ ...prev, [field]: value }));
  }

  function updateFee(index: number, value: string) {
    setFees((prev) =>
      prev.map((f, i) => (i === index ? { ...f, fee: value } : f)),
    );
  }

  // Completeness checks
  const practiceComplete =
    practice.practice_name &&
    practice.provider_name &&
    practice.npi &&
    practice.tax_id &&
    practice.city &&
    practice.state &&
    practice.zip;

  const feesComplete = fees.filter((f) => f.fee && parseFloat(f.fee) > 0).length;
  const clearinghouseComplete = clearinghouse.account_id && clearinghouse.auth_key;

  const TABS: { key: Tab; label: string; badge?: string }[] = [
    { key: "practice", label: "Practice Info" },
    { key: "fees", label: "Fee Schedule" },
    { key: "clearinghouse", label: "Clearinghouse" },
    { key: "status", label: "Setup Status" },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-heading font-bold text-gray-100">
            Practice Setup
          </h1>
          <p className="text-sm font-body text-gray-500 mt-1">
            Configure your practice information for claim submission
          </p>
        </div>
        <button onClick={handleSave} className="btn-primary relative">
          {saved ? "Saved!" : "Save Changes"}
          {saved && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-lime rounded-full" />
          )}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-white/[0.06] overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-heading whitespace-nowrap transition-all duration-200 ${
              tab === t.key
                ? "border-b-2 border-cyan text-cyan font-semibold"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Practice Info Tab */}
      {tab === "practice" && (
        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Practice Details
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Practice Name
                </label>
                <input
                  value={practice.practice_name}
                  onChange={(e) => updatePractice("practice_name", e.target.value)}
                  placeholder="e.g., Smile Dental Care"
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Provider Name
                </label>
                <input
                  value={practice.provider_name}
                  onChange={(e) => updatePractice("provider_name", e.target.value)}
                  placeholder="e.g., Dr. Jane Smith"
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Credentials
                </label>
                <select
                  value={practice.provider_credentials}
                  onChange={(e) => updatePractice("provider_credentials", e.target.value)}
                  className="input-field w-full"
                >
                  <option value="DDS">DDS</option>
                  <option value="DMD">DMD</option>
                  <option value="RDH">RDH</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-1">
              Billing Identifiers
            </h3>
            <p className="text-xs text-gray-600 font-body mb-4">
              Required for electronic claim submission. Find your NPI at{" "}
              <span className="text-cyan">nppes.cms.hhs.gov</span>
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  NPI Number
                </label>
                <input
                  value={practice.npi}
                  onChange={(e) => updatePractice("npi", e.target.value.replace(/\D/g, "").slice(0, 10))}
                  placeholder="10 digits"
                  className="input-field w-full"
                  maxLength={10}
                />
                {practice.npi && practice.npi.length !== 10 && (
                  <p className="text-xs text-amber-400 mt-1">NPI must be 10 digits</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Tax ID / EIN
                </label>
                <input
                  value={practice.tax_id}
                  onChange={(e) => updatePractice("tax_id", e.target.value.replace(/\D/g, "").slice(0, 9))}
                  placeholder="9 digits"
                  className="input-field w-full"
                  maxLength={9}
                />
              </div>
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Taxonomy Code
                </label>
                <input
                  value={practice.taxonomy_code}
                  onChange={(e) => updatePractice("taxonomy_code", e.target.value)}
                  placeholder="1223G0001X"
                  className="input-field w-full"
                />
                <p className="text-xs text-gray-600 mt-1">General dentistry default shown</p>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Practice Address
            </h3>
            <div className="grid grid-cols-1 gap-4">
              <input
                value={practice.address_line1}
                onChange={(e) => updatePractice("address_line1", e.target.value)}
                placeholder="Street address"
                className="input-field w-full"
              />
              <input
                value={practice.address_line2}
                onChange={(e) => updatePractice("address_line2", e.target.value)}
                placeholder="Suite, unit, etc. (optional)"
                className="input-field w-full"
              />
              <div className="grid grid-cols-3 gap-4">
                <input
                  value={practice.city}
                  onChange={(e) => updatePractice("city", e.target.value)}
                  placeholder="City"
                  className="input-field w-full"
                />
                <select
                  value={practice.state}
                  onChange={(e) => updatePractice("state", e.target.value)}
                  className="input-field w-full"
                >
                  <option value="">State</option>
                  {US_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <input
                  value={practice.zip}
                  onChange={(e) => updatePractice("zip", e.target.value.replace(/\D/g, "").slice(0, 5))}
                  placeholder="ZIP"
                  className="input-field w-full"
                  maxLength={5}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <input
                  value={practice.phone}
                  onChange={(e) => updatePractice("phone", e.target.value)}
                  placeholder="Phone"
                  className="input-field w-full"
                />
                <input
                  value={practice.email}
                  onChange={(e) => updatePractice("email", e.target.value)}
                  placeholder="Email"
                  className="input-field w-full"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fee Schedule Tab */}
      {tab === "fees" && (
        <div className="space-y-5">
          <div className="card p-5 border-cyan/20 bg-cyan-50">
            <p className="text-sm text-gray-300 font-body">
              Enter your practice's UCR (usual, customary, and reasonable) fees.
              These are used to calculate claim amounts. Leave blank for any
              procedures you don't perform — you can always add them later.
            </p>
          </div>

          <div className="card overflow-hidden">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="table-header">Code</th>
                  <th className="table-header">Description</th>
                  <th className="table-header w-32">Fee ($)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {fees.map((f, i) => (
                  <tr key={f.cdt_code} className="hover:bg-white/[0.02]">
                    <td className="table-cell">
                      <span className="text-cyan font-heading font-bold text-xs">
                        {f.cdt_code}
                      </span>
                    </td>
                    <td className="table-cell text-gray-400 text-xs">
                      {f.description}
                    </td>
                    <td className="table-cell">
                      <input
                        value={f.fee}
                        onChange={(e) => updateFee(i, e.target.value)}
                        placeholder="0.00"
                        className="input-field w-full text-right text-sm"
                        type="number"
                        step="0.01"
                        min="0"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-gray-600 font-body">
            {feesComplete} of {fees.length} fees entered.
            These are the most common dental procedures — additional codes are
            handled automatically using industry-standard fee estimates.
          </p>
        </div>
      )}

      {/* Clearinghouse Tab */}
      {tab === "clearinghouse" && (
        <div className="space-y-5">
          <div className="card p-5 border-purple-500/20 bg-purple-500/5">
            <p className="text-sm text-gray-300 font-body">
              A clearinghouse connection is only needed for{" "}
              <strong className="text-purple-400">live claim submission</strong>{" "}
              and real-time eligibility checks. All AI features (coding,
              validation, appeals) work without it.
            </p>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Clearinghouse Connection
            </h3>
            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Clearinghouse
                </label>
                <select
                  value={clearinghouse.name}
                  onChange={(e) => updateClearinghouse("name", e.target.value)}
                  className="input-field w-full"
                >
                  <option value="claim.md">Claim.MD (Recommended)</option>
                  <option value="dentalxchange">DentalXChange</option>
                  <option value="availity">Availity</option>
                  <option value="tesia">Tesia (NEA)</option>
                  <option value="change_healthcare">Change Healthcare</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-heading text-gray-500 mb-1">
                    Account ID
                  </label>
                  <input
                    value={clearinghouse.account_id}
                    onChange={(e) => updateClearinghouse("account_id", e.target.value)}
                    placeholder="Your clearinghouse account ID"
                    className="input-field w-full"
                  />
                </div>
                <div>
                  <label className="block text-xs font-heading text-gray-500 mb-1">
                    Auth Key / API Key
                  </label>
                  <input
                    value={clearinghouse.auth_key}
                    onChange={(e) => updateClearinghouse("auth_key", e.target.value)}
                    placeholder="Your API key"
                    className="input-field w-full"
                    type="password"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-heading text-gray-500 mb-1">
                  Environment
                </label>
                <div className="flex gap-3">
                  {["sandbox", "production"].map((env) => (
                    <button
                      key={env}
                      onClick={() => updateClearinghouse("environment", env)}
                      className={`px-4 py-2 rounded-lg text-sm font-heading capitalize transition-all ${
                        clearinghouse.environment === env
                          ? "bg-cyan/10 text-cyan border border-cyan/30"
                          : "bg-white/[0.04] text-gray-500 border border-white/[0.06] hover:text-gray-300"
                      }`}
                    >
                      {env}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-600 mt-2">
                  Use sandbox for testing. Switch to production when ready to submit real claims.
                </p>
              </div>
            </div>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-3">
              Don't have a clearinghouse account?
            </h3>
            <div className="space-y-3 text-sm text-gray-400 font-body">
              <p>
                Most dental practices already have one — it's how you submit
                electronic claims today. Check with your office manager or billing team.
              </p>
              <p>
                If you need a new one, we recommend <strong className="text-cyan">Claim.MD</strong> — they offer
                a free developer sandbox, simple REST API, and route to 1,000+ insurance payers.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Status Tab */}
      {tab === "status" && (
        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Setup Completeness
            </h3>
            <div className="space-y-3">
              <StatusRow
                label="Practice Information"
                complete={!!practiceComplete}
                detail={
                  practiceComplete
                    ? `${practice.practice_name} — NPI: ${practice.npi}`
                    : "Name, NPI, Tax ID, and address required"
                }
              />
              <StatusRow
                label="Fee Schedule"
                complete={feesComplete >= 10}
                partial={feesComplete > 0 && feesComplete < 10}
                detail={`${feesComplete} of ${fees.length} fees entered`}
              />
              <StatusRow
                label="Clearinghouse"
                complete={!!clearinghouseComplete}
                detail={
                  clearinghouseComplete
                    ? `${clearinghouse.name} (${clearinghouse.environment})`
                    : "Optional — only for live claim submission"
                }
              />
            </div>
          </div>

          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              What Works at Each Level
            </h3>
            <div className="space-y-3">
              <FeatureLevel
                level="No Setup Needed"
                color="text-lime border-lime/30 bg-lime/10"
                features={[
                  "AI clinical note parsing (dictation and typing)",
                  "AI CDT code suggestions with confidence scores",
                  "Dental image analysis (X-rays, photos)",
                  "Image-procedure verification",
                  "Documentation completeness checking",
                  "AI appeal letter generation with case law",
                  "Denial risk scoring",
                ]}
              />
              <FeatureLevel
                level="With Practice Info"
                color="text-cyan border-cyan/30 bg-cyan/10"
                features={[
                  "X12 837D dental claim generation (universal EDI format)",
                  "ADA dental claim form PDF download",
                  "Payer-specific frequency rule checking",
                  "Pre-authorization requirement alerts",
                  "Complete pre-submission validation",
                ]}
              />
              <FeatureLevel
                level="With Fee Schedule"
                color="text-amber-400 border-amber-500/30 bg-amber-500/10"
                features={[
                  "Accurate claim amounts on submissions",
                  "Patient responsibility estimates",
                  "Annual benefit tracking",
                  "Revenue impact reporting",
                ]}
              />
              <FeatureLevel
                level="With Clearinghouse"
                color="text-purple-400 border-purple-500/30 bg-purple-500/10"
                features={[
                  "Live electronic claim submission to insurance payers",
                  "Real-time patient eligibility verification",
                  "Automatic ERA (payment/denial) ingestion",
                  "Denial feedback learning — system gets smarter over time",
                ]}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusRow({
  label,
  complete,
  partial,
  detail,
}: {
  label: string;
  complete: boolean;
  partial?: boolean;
  detail: string;
}) {
  return (
    <div className="flex items-center gap-3 bg-navy-900 rounded-lg p-3 border border-white/[0.04]">
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
          complete
            ? "bg-lime/20"
            : partial
              ? "bg-amber-500/20"
              : "bg-white/[0.06]"
        }`}
      >
        {complete ? (
          <svg className="w-3.5 h-3.5 text-lime" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        ) : partial ? (
          <div className="w-2 h-2 rounded-full bg-amber-400" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-gray-600" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-heading font-semibold text-gray-200">{label}</p>
        <p className="text-xs font-body text-gray-500 truncate">{detail}</p>
      </div>
    </div>
  );
}

function FeatureLevel({
  level,
  color,
  features,
}: {
  level: string;
  color: string;
  features: string[];
}) {
  return (
    <div className="bg-navy-900 rounded-lg p-4 border border-white/[0.04]">
      <span
        className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-heading font-semibold border mb-3 ${color}`}
      >
        {level}
      </span>
      <ul className="space-y-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-xs font-body text-gray-400">
            <span className="text-gray-600 mt-0.5 shrink-0">&#x2022;</span>
            {f}
          </li>
        ))}
      </ul>
    </div>
  );
}
