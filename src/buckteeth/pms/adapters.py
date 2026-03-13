import uuid
from abc import ABC, abstractmethod

from buckteeth.pms.schemas import (
    PMSPatient, PMSEncounter, PMSProcedure, PMSTreatmentHistory,
    PMSClaimResult, PMSFeeSchedule, PMSConnectionStatus,
)


class PMSAdapter(ABC):
    """Abstract interface for practice management system integrations."""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> PMSConnectionStatus: ...

    @abstractmethod
    async def pull_patients(self, **filters) -> list[PMSPatient]: ...

    @abstractmethod
    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None: ...

    @abstractmethod
    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory: ...

    @abstractmethod
    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult: ...

    @abstractmethod
    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule: ...


# Sample data for the mock adapter
_MOCK_PATIENTS = [
    PMSPatient(
        external_id="PAT-001", first_name="Jane", last_name="Smith",
        date_of_birth="1985-03-15", gender="F",
        phone="555-0101", email="jane.smith@email.com",
        address="123 Oak St, Los Angeles, CA 90001",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB-001", primary_group_number="GRP-100",
    ),
    PMSPatient(
        external_id="PAT-002", first_name="John", last_name="Doe",
        date_of_birth="1972-07-22", gender="M",
        phone="555-0102", email="john.doe@email.com",
        address="456 Elm St, Los Angeles, CA 90002",
        primary_payer_name="MetLife Dental", primary_payer_id="ML001",
        primary_subscriber_id="SUB-002", primary_group_number="GRP-200",
    ),
    PMSPatient(
        external_id="PAT-003", first_name="Maria", last_name="Smith",
        date_of_birth="1990-11-08", gender="F",
        phone="555-0103",
        primary_payer_name="Cigna Dental", primary_payer_id="CG001",
        primary_subscriber_id="SUB-003", primary_group_number="GRP-300",
    ),
]

_MOCK_ENCOUNTERS = [
    PMSEncounter(
        external_id="ENC-001", patient_external_id="PAT-001",
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        procedures=[
            PMSProcedure(code="D1110", description="Prophylaxis - adult", fee=150.00),
            PMSProcedure(code="D0120", description="Periodic oral evaluation", fee=65.00),
            PMSProcedure(code="D0274", description="Bitewings - four films", fee=85.00),
        ],
        notes="Routine 6-month recall. Healthy dentition, no new findings.",
    ),
    PMSEncounter(
        external_id="ENC-002", patient_external_id="PAT-001",
        provider_name="Dr. Smith", date_of_service="2025-09-10",
        procedures=[
            PMSProcedure(code="D2740", description="Crown - porcelain/ceramic",
                         tooth_number="30", fee=1200.00),
            PMSProcedure(code="D2950", description="Core buildup",
                         tooth_number="30", fee=350.00),
        ],
        notes="Crown prep #30. Large MOD amalgam failing with recurrent decay.",
    ),
    PMSEncounter(
        external_id="ENC-003", patient_external_id="PAT-002",
        provider_name="Dr. Jones", date_of_service="2026-03-12",
        procedures=[
            PMSProcedure(code="D4341", description="SRP - 4+ teeth per quadrant",
                         tooth_number="", surfaces="", fee=275.00),
        ],
        notes="Periodontal therapy UR quadrant. Pockets 5-7mm.",
    ),
]

_MOCK_FEE_SCHEDULE = {
    "D0120": 65.00, "D0150": 95.00, "D0210": 150.00, "D0274": 85.00,
    "D1110": 150.00, "D1120": 95.00, "D2140": 195.00, "D2150": 235.00,
    "D2160": 280.00, "D2161": 320.00, "D2330": 175.00, "D2331": 210.00,
    "D2332": 250.00, "D2335": 290.00, "D2391": 215.00, "D2392": 260.00,
    "D2393": 300.00, "D2394": 340.00, "D2740": 1200.00, "D2750": 1100.00,
    "D2950": 350.00, "D3310": 800.00, "D3320": 950.00, "D3330": 1100.00,
    "D4341": 275.00, "D4342": 200.00, "D7140": 225.00, "D7210": 350.00,
}


class MockPMSAdapter(PMSAdapter):
    """Mock PMS adapter for development and testing."""

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        return PMSConnectionStatus(
            connected=True,
            pms_name="MockPMS",
            version="1.0.0",
            last_sync="2026-03-12T10:00:00Z",
        )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        patients = _MOCK_PATIENTS
        if "last_name" in filters:
            patients = [p for p in patients if p.last_name == filters["last_name"]]
        if "external_id" in filters:
            patients = [p for p in patients if p.external_id == filters["external_id"]]
        return patients

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        for enc in _MOCK_ENCOUNTERS:
            if (enc.patient_external_id == patient_external_id
                    and enc.date_of_service == date_of_service):
                return enc
        return None

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        encounters = [e for e in _MOCK_ENCOUNTERS
                      if e.patient_external_id == patient_external_id]
        return PMSTreatmentHistory(
            patient_external_id=patient_external_id,
            encounters=encounters,
        )

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        return PMSClaimResult(
            external_claim_id=f"CLM-{uuid.uuid4().hex[:8].upper()}",
            status="accepted",
            message="Claim accepted by MockPMS",
        )

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        return PMSFeeSchedule(payer_id=payer_id, fees=_MOCK_FEE_SCHEDULE)
