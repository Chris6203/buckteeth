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
