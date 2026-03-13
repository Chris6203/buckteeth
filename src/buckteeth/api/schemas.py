import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Patient ──────────────────────────────────────────────────────────────


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str


class PatientResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class InsurancePlanCreate(BaseModel):
    payer_name: str
    payer_id: str
    subscriber_id: str
    group_number: str
    plan_type: str


class InsurancePlanResponse(BaseModel):
    id: uuid.UUID
    payer_name: str
    payer_id: str
    subscriber_id: str
    group_number: str
    plan_type: str

    model_config = {"from_attributes": True}


# ── Encounter ────────────────────────────────────────────────────────────


class EncounterFromNotesRequest(BaseModel):
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
    notes: str


class ClinicalProcedureResponse(BaseModel):
    id: uuid.UUID
    description: str
    tooth_numbers: Any | None = None
    surfaces: Any | None = None
    quadrant: str | None = None
    diagnosis: str | None = None

    model_config = {"from_attributes": True}


class EncounterResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
    raw_notes: str | None = None
    raw_input_type: str
    status: str
    procedures: list[ClinicalProcedureResponse] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Coding ───────────────────────────────────────────────────────────────


class CodeEncounterRequest(BaseModel):
    payer_id: str = "default"


class CodedProcedureResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    confidence_score: int
    ai_reasoning: str
    flags: Any | None = None
    icd10_codes: Any | None = None

    model_config = {"from_attributes": True}


class CodedEncounterResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    review_status: str
    coded_procedures: list[CodedProcedureResponse] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OverrideProcedureRequest(BaseModel):
    cdt_code: str
    cdt_description: str
    override_reason: str


# ── Claims ───────────────────────────────────────────────────────────────


class ClaimCreateRequest(BaseModel):
    coded_encounter_id: uuid.UUID


class ClaimNarrativeResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    narrative_text: str
    generated_by: str
    payer_tailored: bool = False
    model_config = {"from_attributes": True}


class ClaimProcedureAPIResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    fee_submitted: float | None = None
    model_config = {"from_attributes": True}


class ClaimResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    coded_encounter_id: uuid.UUID
    provider_name: str
    date_of_service: str
    status: str
    primary_payer_name: str
    primary_payer_id: str
    primary_subscriber_id: str
    primary_group_number: str
    secondary_payer_name: str | None = None
    preauth_required: bool = False
    total_fee_submitted: float | None = None
    procedures: list[ClaimProcedureAPIResponse] = []
    narratives: list[ClaimNarrativeResponse] = []
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class ClaimStatusUpdate(BaseModel):
    status: str


# ── Submissions ──────────────────────────────────────────────────────────


class SubmitClaimRequest(BaseModel):
    claim_id: uuid.UUID


class SubmitBatchRequest(BaseModel):
    claim_ids: list[uuid.UUID]


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    channel: str
    clearinghouse_name: str | None = None
    tracking_number: str | None = None
    confirmation_number: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class EligibilityRequest(BaseModel):
    patient_id: uuid.UUID
    payer_id: str
    subscriber_id: str
    date_of_service: str


class EligibilityCheckResponse(BaseModel):
    eligible: bool
    annual_maximum: float | None = None
    annual_used: float | None = None
    annual_remaining: float | None = None
    deductible: float | None = None
    deductible_met: float | None = None


# ── Denials ──────────────────────────────────────────────────────────────


class CreateDenialRequest(BaseModel):
    claim_id: uuid.UUID
    denial_reason_code: str
    denial_reason_description: str
    denied_amount: float
    payer_name: str


class DenialResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    denial_reason_code: str
    denial_reason_description: str
    denied_amount: float | None
    payer_name: str
    status: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class GenerateAppealRequest(BaseModel):
    clinical_notes: str
    state: str = "CA"


class AppealDocumentResponse(BaseModel):
    id: uuid.UUID
    denial_id: uuid.UUID
    appeal_text: str
    case_law_citations: Any | None = None
    generated_by: str
    status: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class SendCommissionerLetterRequest(BaseModel):
    patient_address: str
    provider_address: str
    clinical_notes: str
    state: str


class CommissionerLetterAPIResponse(BaseModel):
    id: uuid.UUID
    denial_id: uuid.UUID
    state: str
    commissioner_name: str
    letter_text: str
    mail_status: str
    mail_tracking_id: str | None = None
    trigger_type: str
    created_at: datetime | None = None
    model_config = {"from_attributes": True}
