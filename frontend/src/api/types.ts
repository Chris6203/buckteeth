// ── Patient ──────────────────────────────────────────────────────────

export interface PatientCreate {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
}

export interface InsurancePlan {
  id: string;
  payer_name: string;
  payer_id: string;
  subscriber_id: string;
  group_number: string;
  plan_type: string;
}

export interface InsurancePlanCreate {
  payer_name: string;
  payer_id: string;
  subscriber_id: string;
  group_number: string;
  plan_type: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  insurance_plans?: InsurancePlan[];
  created_at: string | null;
}

export interface PracticeSettings {
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
  clearinghouse_name: string;
  clearinghouse_account_id: string;
  clearinghouse_environment: string;
  fee_schedule: Record<string, number>;
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

// ── Documentation Template ───────────────────────────────────────────

export interface DocumentationPrompt {
  category: string;
  label: string;
  description: string;
  required: boolean;
  for_procedure: string;
  input_type: string;
  options: string[];
}

export interface DocumentationTemplate {
  prompts: DocumentationPrompt[];
  summary: string;
  required_count: number;
  total_count: number;
}

// ── Image Quality ────────────────────────────────────────────────────

export interface ImageQualityIssue {
  code: string;
  severity: "error" | "warning";
  message: string;
  suggestion: string;
}

export interface ImageQualityResult {
  passed: boolean;
  issues: ImageQualityIssue[];
  metadata: Record<string, unknown>;
  error_count: number;
  warning_count: number;
}

// ── Pre-Submission Validation ────────────────────────────────────────

export interface ValidationIssue {
  code: string;
  severity: "block" | "warn" | "info";
  category: string;
  message: string;
  cdt_code: string | null;
  recommendation: string | null;
  denial_probability: number;
}

export interface ValidationResult {
  issues: ValidationIssue[];
  passed: boolean;
  overall_denial_risk: number;
  summary: string;
  blocker_count: number;
  warning_count: number;
}

// ── Documentation Check ──────────────────────────────────────────────

export interface DocumentationAlert {
  cdt_code: string;
  cdt_description: string;
  missing_type: string;
  label: string;
  description: string;
  severity: "required" | "recommended";
  tooth_number: string | null;
}

export interface DocumentationCheck {
  alerts: DocumentationAlert[];
  complete: boolean;
  summary: string;
}

// ── Image Verification ───────────────────────────────────────────────

export interface ProcedureVerification {
  cdt_code: string;
  status: "supported" | "unsupported" | "inconclusive";
  confidence: number;
  finding: string;
  concern: string | null;
  recommendation: string | null;
}

export interface MissedFinding {
  description: string;
  tooth_number: string | null;
  suggested_code: string | null;
  suggested_description: string | null;
  reasoning: string | null;
}

export interface ImageVerification {
  verifications: ProcedureVerification[];
  missed_findings: MissedFinding[];
  overall_assessment: {
    documentation_strength: "strong" | "moderate" | "weak";
    denial_risk: "low" | "medium" | "high";
    summary: string;
  };
}

// ── Health ────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
}
