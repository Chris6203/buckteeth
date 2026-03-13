import type {
  Patient,
  PatientCreate,
  Encounter,
  EncounterFromNotesRequest,
  CodedEncounter,
  Claim,
  RiskAssessment,
  Submission,
  Denial,
  AppealDocument,
  GenerateAppealRequest,
  HealthResponse,
} from "./types";

const BASE = "";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001";

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Tenant-ID": localStorage.getItem("tenantId") ?? DEFAULT_TENANT,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: headers(),
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

// ── Health ────────────────────────────────────────────────────────────

export const health = () => request<HealthResponse>("/health");

// ── Patients ─────────────────────────────────────────────────────────

export const listPatients = () => request<Patient[]>("/v1/patients");

export const createPatient = (data: PatientCreate) =>
  request<Patient>("/v1/patients", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getPatient = (id: string) => request<Patient>(`/v1/patients/${id}`);

// ── Encounters ───────────────────────────────────────────────────────

export const createEncounterFromNotes = (data: EncounterFromNotesRequest) =>
  request<Encounter>("/v1/encounters/from-notes", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getEncounter = (id: string) =>
  request<Encounter>(`/v1/encounters/${id}`);

// ── Coding ───────────────────────────────────────────────────────────

export const codeEncounter = (encounterId: string, payerId = "default") =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/code`, {
    method: "POST",
    body: JSON.stringify({ payer_id: payerId }),
  });

export const getCodedEncounter = (encounterId: string) =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/coded`);

export const approveCodedEncounter = (encounterId: string) =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/coded/approve`, {
    method: "POST",
  });

// ── Claims ───────────────────────────────────────────────────────────

export const listClaims = (status?: string) => {
  const qs = status ? `?status=${status}` : "";
  return request<Claim[]>(`/v1/claims${qs}`);
};

export const getClaim = (id: string) => request<Claim>(`/v1/claims/${id}`);

export const createClaim = (codedEncounterId: string) =>
  request<Claim>("/v1/claims", {
    method: "POST",
    body: JSON.stringify({ coded_encounter_id: codedEncounterId }),
  });

export const assessRisk = (claimId: string) =>
  request<RiskAssessment>(`/v1/claims/${claimId}/assess-risk`, {
    method: "POST",
    body: JSON.stringify({}),
  });

// ── Submissions ──────────────────────────────────────────────────────

export const submitClaim = (claimId: string) =>
  request<Submission>("/v1/submissions/submit", {
    method: "POST",
    body: JSON.stringify({ claim_id: claimId }),
  });

export const listSubmissions = () => request<Submission[]>("/v1/submissions");

// ── Denials ──────────────────────────────────────────────────────────

export const listDenials = (status?: string) => {
  const qs = status ? `?status=${status}` : "";
  return request<Denial[]>(`/v1/denials${qs}`);
};

export const getDenial = (id: string) => request<Denial>(`/v1/denials/${id}`);

export const generateAppeal = (denialId: string, data: GenerateAppealRequest) =>
  request<AppealDocument>(`/v1/denials/${denialId}/generate-appeal`, {
    method: "POST",
    body: JSON.stringify(data),
  });
