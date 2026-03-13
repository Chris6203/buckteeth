from dataclasses import dataclass, field


@dataclass
class PMSPatient:
    external_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    primary_payer_name: str | None = None
    primary_payer_id: str | None = None
    primary_subscriber_id: str | None = None
    primary_group_number: str | None = None


@dataclass
class PMSProcedure:
    code: str
    description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    fee: float = 0.0
    status: str = "completed"  # completed, planned, in_progress


@dataclass
class PMSEncounter:
    external_id: str
    patient_external_id: str
    provider_name: str
    date_of_service: str
    procedures: list[PMSProcedure] = field(default_factory=list)
    notes: str | None = None


@dataclass
class PMSTreatmentHistory:
    patient_external_id: str
    encounters: list[PMSEncounter] = field(default_factory=list)


@dataclass
class PMSClaimResult:
    external_claim_id: str
    status: str  # accepted, rejected, error
    message: str | None = None


@dataclass
class PMSFeeSchedule:
    payer_id: str
    fees: dict[str, float] = field(default_factory=dict)  # cdt_code -> fee


@dataclass
class PMSConnectionStatus:
    connected: bool
    pms_name: str
    version: str | None = None
    last_sync: str | None = None
    error: str | None = None
