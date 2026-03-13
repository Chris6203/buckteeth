import { useEffect, useState } from "react";
import { listPatients, createPatient } from "../api/client";
import type { Patient, PatientCreate } from "../api/types";

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create patient");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Patients</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          {showForm ? "Cancel" : "Add Patient"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {showForm && <CreatePatientForm onSubmit={handleCreate} />}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : patients.length === 0 ? (
        <p className="text-gray-500">No patients found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  DOB
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Gender
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {patients.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {p.first_name} {p.last_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {p.date_of_birth}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {p.gender}
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
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-lg border border-gray-200 p-4 mb-6"
    >
      <div className="grid grid-cols-2 gap-4">
        <input
          placeholder="First name"
          value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          placeholder="Last name"
          value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          type="date"
          value={form.date_of_birth}
          onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <select
          value={form.gender}
          onChange={(e) => setForm({ ...form, gender: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        >
          <option value="">Gender</option>
          <option value="M">Male</option>
          <option value="F">Female</option>
          <option value="O">Other</option>
        </select>
      </div>
      <button
        type="submit"
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
      >
        Create Patient
      </button>
    </form>
  );
}
