import { useEffect, useState } from "react";
import {
  listProviders,
  createProvider,
  updateProvider,
  deactivateProvider,
} from "../api/client";
import type { Provider, ProviderCreate } from "../api/types";
import { useToast } from "../components/Toast";

const CREDENTIAL_OPTIONS = ["DDS", "DMD", "RDH"];

const EMPTY_FORM: ProviderCreate = {
  first_name: "",
  last_name: "",
  credentials: "DDS",
  npi: "",
  specialty: "General Dentistry",
  email: "",
  phone: "",
};

export default function Providers() {
  const { addToast } = useToast();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProviderCreate>({ ...EMPTY_FORM });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const data = await listProviders();
      setProviders(data);
    } catch (e: unknown) {
      addToast("error", e instanceof Error ? e.message : "Failed to load providers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function openAdd() {
    setEditingId(null);
    setForm({ ...EMPTY_FORM });
    setShowForm(true);
  }

  function openEdit(p: Provider) {
    setEditingId(p.id);
    setForm({
      first_name: p.first_name,
      last_name: p.last_name,
      credentials: p.credentials,
      npi: p.npi || "",
      specialty: p.specialty || "General Dentistry",
      email: p.email || "",
      phone: p.phone || "",
    });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.first_name.trim() || !form.last_name.trim()) {
      addToast("error", "First and last name are required");
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await updateProvider(editingId, form);
        addToast("success", "Provider updated");
      } else {
        await createProvider(form);
        addToast("success", "Provider created");
      }
      setShowForm(false);
      setEditingId(null);
      await load();
    } catch (e: unknown) {
      addToast("error", e instanceof Error ? e.message : "Failed to save provider");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(p: Provider) {
    if (!confirm(`Deactivate Dr. ${p.first_name} ${p.last_name}?`)) return;
    try {
      await deactivateProvider(p.id);
      addToast("success", "Provider deactivated");
      await load();
    } catch (e: unknown) {
      addToast("error", e instanceof Error ? e.message : "Failed to deactivate provider");
    }
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-heading font-bold text-white">Providers</h1>
          <p className="text-sm font-body text-gray-400 mt-1">
            Manage your practice providers
          </p>
        </div>
        <button onClick={openAdd} className="btn-primary text-sm flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Provider
        </button>
      </div>

      {/* Inline Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="card p-5 mb-6 space-y-4">
          <h3 className="text-sm font-heading font-semibold text-gray-300">
            {editingId ? "Edit Provider" : "New Provider"}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">First Name *</label>
              <input
                className="input-field"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                placeholder="First name"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">Last Name *</label>
              <input
                className="input-field"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                placeholder="Last name"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">Credentials</label>
              <select
                className="input-field"
                value={form.credentials}
                onChange={(e) => setForm({ ...form, credentials: e.target.value })}
              >
                {CREDENTIAL_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">NPI</label>
              <input
                className="input-field"
                value={form.npi}
                onChange={(e) => setForm({ ...form, npi: e.target.value })}
                placeholder="10-digit NPI"
                maxLength={10}
              />
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">Specialty</label>
              <input
                className="input-field"
                value={form.specialty}
                onChange={(e) => setForm({ ...form, specialty: e.target.value })}
                placeholder="Specialty"
              />
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">Email</label>
              <input
                className="input-field"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email"
              />
            </div>
            <div>
              <label className="block text-xs font-body text-gray-400 mb-1">Phone</label>
              <input
                className="input-field"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="Phone"
              />
            </div>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button type="submit" className="btn-primary text-sm" disabled={saving}>
              {saving ? "Saving..." : editingId ? "Update" : "Create"}
            </button>
            <button
              type="button"
              className="btn-secondary text-sm"
              onClick={() => { setShowForm(false); setEditingId(null); }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Provider Cards */}
      {loading ? (
        <div className="text-center py-16">
          <div className="inline-block w-8 h-8 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
          <p className="text-sm text-gray-400 mt-3 font-body">Loading providers...</p>
        </div>
      ) : providers.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 mx-auto text-gray-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
          <p className="text-gray-400 font-body">No providers yet</p>
          <p className="text-sm text-gray-500 font-body mt-1">Click "Add Provider" to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {providers.map((p) => (
            <div key={p.id} className="card p-5 flex flex-col gap-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-heading font-semibold text-white">
                    Dr. {p.first_name} {p.last_name}, {p.credentials}
                  </h3>
                  <p className="text-xs text-cyan font-body mt-0.5">{p.specialty || "General Dentistry"}</p>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => openEdit(p)}
                    className="p-1.5 text-gray-400 hover:text-cyan transition-colors"
                    title="Edit"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeactivate(p)}
                    className="p-1.5 text-gray-400 hover:text-rose-400 transition-colors"
                    title="Deactivate"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M22 10.5h-6m-2.25-4.125a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0ZM4 19.235v-.11a6.375 6.375 0 0 1 12.75 0v.109A12.318 12.318 0 0 1 10.374 21c-2.331 0-4.512-.645-6.374-1.766Z" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="space-y-1.5 text-sm font-body">
                {p.npi && (
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-gray-500 text-xs w-12">NPI</span>
                    <span>{p.npi}</span>
                  </div>
                )}
                {p.email && (
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-gray-500 text-xs w-12">Email</span>
                    <span>{p.email}</span>
                  </div>
                )}
                {p.phone && (
                  <div className="flex items-center gap-2 text-gray-400">
                    <span className="text-gray-500 text-xs w-12">Phone</span>
                    <span>{p.phone}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
