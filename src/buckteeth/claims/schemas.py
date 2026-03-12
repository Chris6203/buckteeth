import uuid
from pydantic import BaseModel


class NarrativeRequest(BaseModel):
    cdt_code: str
    procedure_description: str
    clinical_notes: str
    diagnosis: str | None = None
    tooth_number: str | None = None
    surfaces: str | None = None
    payer_name: str | None = None


class NarrativeResponse(BaseModel):
    cdt_code: str
    narrative_text: str
    payer_tailored: bool = False


class ClaimBuildRequest(BaseModel):
    coded_encounter_id: uuid.UUID
    primary_payer_id: str | None = None


class ClaimProcedureDetail(BaseModel):
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    fee_submitted: float | None = None
    narrative: NarrativeResponse | None = None


class ClaimDetail(BaseModel):
    claim_id: uuid.UUID
    patient_name: str
    provider_name: str
    date_of_service: str
    status: str
    primary_payer_name: str
    primary_subscriber_id: str
    primary_group_number: str
    secondary_payer_name: str | None = None
    total_fee_submitted: float | None = None
    procedures: list[ClaimProcedureDetail]
    narratives: list[NarrativeResponse] = []
    preauth_required: bool = False
    preauth_number: str | None = None
    procedure_count: int = 0
    has_narratives: bool = False
    has_preauth: bool = False
