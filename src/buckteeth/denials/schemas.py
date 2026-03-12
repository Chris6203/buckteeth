from pydantic import BaseModel


class AppealRequest(BaseModel):
    denial_reason_code: str
    denial_reason_description: str
    denied_amount: float
    payer_name: str
    cdt_code: str
    procedure_description: str
    clinical_notes: str
    patient_name: str
    date_of_service: str
    provider_name: str
    state: str  # for state-specific case law


class AppealResponse(BaseModel):
    appeal_text: str
    case_law_citations: list[str]
    key_arguments: list[str]
    recommended_attachments: list[str]


class CommissionerLetterRequest(BaseModel):
    denial_reason_code: str
    denial_reason_description: str
    denied_amount: float
    payer_name: str
    patient_name: str
    patient_address: str
    provider_name: str
    provider_address: str
    date_of_service: str
    cdt_code: str
    procedure_description: str
    clinical_notes: str
    state: str
    appeal_already_filed: bool = True


class CommissionerLetterResponse(BaseModel):
    letter_text: str
    commissioner_name: str
    commissioner_address: str
    case_law_citations: list[str]
    regulatory_citations: list[str]
