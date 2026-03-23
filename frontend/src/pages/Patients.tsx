import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listPatients,
  createPatient,
  addInsurancePlan,
  deleteInsurancePlan,
} from "../api/client";
import type { Patient, PatientCreate, InsurancePlanCreate } from "../api/types";
import { formatDate } from "../utils";
import ToothChart from "../components/ToothChart";
import BenefitsEntry, {
  DEFAULT_BENEFITS,
  type BenefitsData,
} from "../components/BenefitsEntry";
import { useToast } from "../components/Toast";

const AVATAR_COLORS = [
  "bg-cyan/20 text-cyan",
  "bg-lime/20 text-lime",
  "bg-purple-500/20 text-purple-400",
  "bg-amber-500/20 text-amber-400",
  "bg-rose-500/20 text-rose-400",
  "bg-blue-500/20 text-blue-400",
];

function getInitials(first: string, last: string): string {
  return `${(first[0] || "").toUpperCase()}${(last[0] || "").toUpperCase()}`;
}

function getAvatarColor(name: string): string {
  let hash = 0;
  for (const ch of name) hash = ch.charCodeAt(0) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function formatGender(raw: string): string {
  const n = raw.toLowerCase().trim();
  if (n === "m" || n === "male") return "Male";
  if (n === "f" || n === "female") return "Female";
  if (n === "o" || n === "other") return "Other";
  return raw;
}

function useLocalStorageState<T>(key: string | null, defaultValue: T): [T, (val: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (!key) return defaultValue;
    try {
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  const set = useCallback(
    (val: T) => {
      setValue(val);
      if (key) {
        localStorage.setItem(key, JSON.stringify(val));
      }
    },
    [key],
  );

  // Reset when key changes
  useEffect(() => {
    if (!key) {
      setValue(defaultValue);
      return;
    }
    try {
      const stored = localStorage.getItem(key);
      setValue(stored ? JSON.parse(stored) : defaultValue);
    } catch {
      setValue(defaultValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return [value, set];
}

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showInsuranceForm, setShowInsuranceForm] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const { addToast } = useToast();

  const [missingTeeth, setMissingTeeth] = useLocalStorageState<Record<string, string>>(
    expandedId ? `pp_patient_${expandedId}_teeth` : null,
    {},
  );
  const [benefits, setBenefits] = useLocalStorageState<BenefitsData>(
    expandedId ? `pp_patient_${expandedId}_benefits` : null,
    DEFAULT_BENEFITS,
  );

  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients() {
    try {
      setLoading(true);
      const data = await listPatients();
      setPatients(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load patients");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(data: PatientCreate) {
    try {
      await createPatient(data);
      setShowForm(false);
      await loadPatients();
      addToast("success", "Patient created");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create patient",
      );
    }
  }

  async function handleAddInsurance(patientId: string, data: InsurancePlanCreate) {
    try {
      await addInsurancePlan(patientId, data);
      setShowInsuranceForm(null);
      await loadPatients();
      addToast("success", "Insurance added");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to add insurance plan",
      );
    }
  }

  async function handleDeleteInsurance(patientId: string, planId: string) {
    try {
      await deleteInsurancePlan(patientId, planId);
      await loadPatients();
      addToast("info", "Insurance removed");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to remove insurance plan",
      );
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-heading font-bold text-gray-100">
            Patients
          </h1>
          <p className="text-sm font-body text-gray-500 mt-1">
            {loading
              ? "Manage patient records and insurance"
              : `${patients.length} patient${patients.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className={showForm ? "btn-secondary" : "btn-primary"}
        >
          {showForm ? "Cancel" : "Add Patient"}
        </button>
      </div>

      {error && (
        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-body">
          {error}
        </div>
      )}

      {showForm && <CreatePatientForm onSubmit={handleCreate} />}

      {!loading && patients.length > 0 && (
        <div className="mb-5">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search patients..."
            className="input-field w-full sm:w-72"
          />
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
          <span className="font-body text-sm">Loading...</span>
        </div>
      ) : patients.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
          <p className="text-gray-400 font-body">No patients yet</p>
          <p className="text-gray-600 font-body text-sm mt-1">
            Add your first patient to get started
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {patients.filter((p) => {
            if (!searchQuery.trim()) return true;
            const fullName = `${p.first_name} ${p.last_name}`.toLowerCase();
            return fullName.includes(searchQuery.toLowerCase().trim());
          }).map((p) => {
            const expanded = expandedId === p.id;
            const plans = p.insurance_plans || [];
            const primaryPlan = plans.find((ip) => ip.plan_type === "primary");

            return (
              <div key={p.id} className="card overflow-hidden">
                {/* Patient row */}
                <button
                  onClick={() => setExpandedId(expanded ? null : p.id)}
                  className="w-full flex items-center gap-4 p-4 hover:bg-white/[0.02] transition-colors text-left"
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-heading font-bold shrink-0 ${getAvatarColor(p.first_name + p.last_name)}`}
                  >
                    {getInitials(p.first_name, p.last_name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-100">
                      {p.first_name} {p.last_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      DOB: {formatDate(p.date_of_birth)} &middot; {formatGender(p.gender)}
                      {primaryPlan && (
                        <span className="ml-2 text-cyan">
                          &middot; {primaryPlan.payer_name}
                        </span>
                      )}
                      {!primaryPlan && plans.length === 0 && (
                        <span className="ml-2 text-amber-400">
                          &middot; No insurance
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Link
                      to="/encounters"
                      onClick={(e) => e.stopPropagation()}
                      className="text-cyan hover:text-cyan-400 text-xs font-heading font-semibold transition-colors"
                    >
                      New Encounter
                    </Link>
                    <svg
                      className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? "rotate-180" : ""}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                  </div>
                </button>

                {/* Expanded details */}
                {expanded && (
                  <div className="px-4 pb-4 border-t border-white/[0.04]">
                    {/* Quick actions */}
                    <div className="flex items-center gap-2 mt-4 mb-4">
                      <Link
                        to="/claims"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-heading font-semibold bg-navy-900 border border-white/[0.08] text-gray-300 hover:border-cyan/40 hover:text-cyan transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                        </svg>
                        View Claims
                      </Link>
                      <Link
                        to="/encounters"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-heading font-semibold bg-cyan/10 border border-cyan/30 text-cyan hover:bg-cyan/20 transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                        New Encounter
                      </Link>
                      <Link
                        to="/encounters"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-heading font-semibold bg-navy-900 border border-white/[0.08] text-gray-300 hover:border-lime/40 hover:text-lime transition-colors"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                        </svg>
                        View Encounters
                      </Link>
                    </div>

                    <div className="mt-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-xs font-heading font-semibold text-gray-400 uppercase tracking-wider">
                          Insurance Plans
                        </h4>
                        <button
                          onClick={() =>
                            setShowInsuranceForm(
                              showInsuranceForm === p.id ? null : p.id,
                            )
                          }
                          className="text-xs text-cyan hover:text-cyan-400 font-heading font-semibold transition-colors"
                        >
                          {showInsuranceForm === p.id
                            ? "Cancel"
                            : "+ Add Insurance"}
                        </button>
                      </div>

                      {showInsuranceForm === p.id && (
                        <InsuranceForm
                          onSubmit={(data) => handleAddInsurance(p.id, data)}
                        />
                      )}

                      {plans.length === 0 ? (
                        <p className="text-sm text-gray-600 font-body py-2">
                          No insurance plans on file. Add one to enable claim
                          submission.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {plans.map((plan) => (
                            <div
                              key={plan.id}
                              className="flex items-center justify-between bg-navy-900 rounded-lg p-3 border border-white/[0.04]"
                            >
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-gray-200">
                                    {plan.payer_name}
                                  </span>
                                  <span
                                    className={`text-xs font-heading font-semibold px-1.5 py-0.5 rounded ${
                                      plan.plan_type === "primary"
                                        ? "bg-cyan/10 text-cyan border border-cyan/30"
                                        : "bg-white/[0.06] text-gray-500 border border-white/[0.08]"
                                    }`}
                                  >
                                    {plan.plan_type}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-500 mt-1">
                                  ID: {plan.subscriber_id} &middot; Group:{" "}
                                  {plan.group_number} &middot; Payer ID:{" "}
                                  {plan.payer_id}
                                </p>
                              </div>
                              <button
                                onClick={() =>
                                  handleDeleteInsurance(p.id, plan.id)
                                }
                                className="text-gray-600 hover:text-red-400 transition-colors p-1"
                                title="Remove plan"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                                </svg>
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Tooth Chart */}
                    <div className="mt-6">
                      <h4 className="text-xs font-heading font-semibold text-gray-400 uppercase tracking-wider mb-3">
                        Tooth Chart
                      </h4>
                      <div className="bg-navy-900 rounded-lg p-4 border border-white/[0.04]">
                        <ToothChart
                          missingTeeth={missingTeeth}
                          onChange={setMissingTeeth}
                        />
                      </div>
                    </div>

                    {/* Benefits — only shown when patient has insurance */}
                    {plans.length > 0 && (
                      <div className="mt-6">
                        <h4 className="text-xs font-heading font-semibold text-gray-400 uppercase tracking-wider mb-3">
                          Benefits
                        </h4>
                        <div className="bg-navy-900 rounded-lg p-4 border border-white/[0.04]">
                          <BenefitsEntry
                            benefits={benefits}
                            onChange={setBenefits}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CreatePatientForm({
  onSubmit,
}: {
  onSubmit: (data: PatientCreate) => void;
}) {
  const [form, setForm] = useState<PatientCreate>({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    gender: "",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="card p-5 mb-6">
      <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
        New Patient
      </h3>
      <div className="grid grid-cols-2 gap-4">
        <input
          placeholder="First name"
          value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          className="input-field"
          required
        />
        <input
          placeholder="Last name"
          value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          className="input-field"
          required
        />
        <input
          type="date"
          value={form.date_of_birth}
          onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
          className="input-field"
          required
        />
        <select
          value={form.gender}
          onChange={(e) => setForm({ ...form, gender: e.target.value })}
          className="input-field"
          required
        >
          <option value="">Gender</option>
          <option value="M">Male</option>
          <option value="F">Female</option>
          <option value="O">Other</option>
        </select>
      </div>
      <button type="submit" className="btn-primary mt-4">
        Create Patient
      </button>
    </form>
  );
}

function InsuranceForm({
  onSubmit,
}: {
  onSubmit: (data: InsurancePlanCreate) => void;
}) {
  const [form, setForm] = useState<InsurancePlanCreate>({
    payer_name: "",
    payer_id: "",
    subscriber_id: "",
    group_number: "",
    plan_type: "primary",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-navy-900 rounded-lg p-4 border border-cyan/20 mb-3"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input
          placeholder="Insurance company (e.g., Delta Dental)"
          value={form.payer_name}
          onChange={(e) => setForm({ ...form, payer_name: e.target.value })}
          className="input-field"
          required
        />
        <input
          placeholder="Payer ID (e.g., DDCA1)"
          value={form.payer_id}
          onChange={(e) => setForm({ ...form, payer_id: e.target.value })}
          className="input-field"
          required
        />
        <input
          placeholder="Subscriber / Member ID"
          value={form.subscriber_id}
          onChange={(e) => setForm({ ...form, subscriber_id: e.target.value })}
          className="input-field"
          required
        />
        <input
          placeholder="Group number"
          value={form.group_number}
          onChange={(e) => setForm({ ...form, group_number: e.target.value })}
          className="input-field"
          required
        />
        <select
          value={form.plan_type}
          onChange={(e) => setForm({ ...form, plan_type: e.target.value })}
          className="input-field"
        >
          <option value="primary">Primary</option>
          <option value="secondary">Secondary</option>
        </select>
      </div>
      <button type="submit" className="btn-primary mt-3 text-sm">
        Add Insurance Plan
      </button>
    </form>
  );
}
