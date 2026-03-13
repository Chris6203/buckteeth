// ── Patient ──────────────────────────────────────────────────────────

export interface PatientCreate {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  created_at: string | null;
}

// ── Encounter ────────────────────────────────────────────────────────

export interface ClinicalProcedure {
  id: string;
  description: string;
  tooth_numbers: number[] | null;
  surfaces: string[] | null;
  quadrant: string | null;
  diagnosis: string | null;
}

export interface Encounter {
  id: string;
  patient_id: string;
  provider_name: string;
  date_of_service: string;
  raw_notes: string | null;
  raw_input_type: string;
  status: string;
  procedures: ClinicalProcedure[];
  created_at: string | null;
}

export interface EncounterFromNotesRequest {
  patient_id: string;
  provider_name: string;
  date_of_service: string;
  notes: string;
}

// ── Coding ───────────────────────────────────────────────────────────

export interface CodedProcedure {
  id: string;
  cdt_code: string;
  cdt_description: string;
  tooth_number: string | null;
  surfaces: string | null;
  quadrant: string | null;
  confidence_score: number;
  ai_reasoning: string;
  flags: unknown;
  icd10_codes: unknown;
}

export interface CodedEncounter {
  id: string;
  encounter_id: string;
  review_status: string;
  coded_procedures: CodedProcedure[];
  created_at: string | null;
}

// ── Claims ───────────────────────────────────────────────────────────

export interface ClaimProcedure {
  id: string;
  cdt_code: string;
  cdt_description: string;
  tooth_number: string | null;
  surfaces: string | null;
  quadrant: string | null;
  fee_submitted: number | null;
}

export interface ClaimNarrative {
  id: string;
  cdt_code: string;
  narrative_text: string;
  generated_by: string;
  payer_tailored: boolean;
}

export interface Claim {
  id: string;
  patient_id: string;
  coded_encounter_id: string;
  provider_name: string;
  date_of_service: string;
  status: string;
  primary_payer_name: string;
  primary_payer_id: string;
  primary_subscriber_id: string;
  primary_group_number: string;
  secondary_payer_name: string | null;
  preauth_required: boolean;
  total_fee_submitted: number | null;
  procedures: ClaimProcedure[];
  narratives: ClaimNarrative[];
  created_at: string | null;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: string;
  risk_factors: string[];
  recommendations: string[];
}

// ── Submissions ──────────────────────────────────────────────────────

export interface Submission {
  id: string;
  claim_id: string;
  channel: string;
  clearinghouse_name: string | null;
  tracking_number: string | null;
  confirmation_number: string | null;
  status: string;
  error_message: string | null;
  created_at: string | null;
}

// ── Denials ──────────────────────────────────────────────────────────

export interface Denial {
  id: string;
  claim_id: string;
  denial_reason_code: string;
  denial_reason_description: string;
  denied_amount: number | null;
  payer_name: string;
  status: string;
  created_at: string | null;
}

export interface AppealDocument {
  id: string;
  denial_id: string;
  appeal_text: string;
  case_law_citations: unknown;
  generated_by: string;
  status: string;
  created_at: string | null;
}

export interface GenerateAppealRequest {
  clinical_notes: string;
  state: string;
}

// ── Health ────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
}
