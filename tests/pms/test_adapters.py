import pytest
from buckteeth.pms.adapters import MockPMSAdapter
from buckteeth.pms.schemas import (
    PMSPatient, PMSEncounter, PMSTreatmentHistory,
    PMSClaimResult, PMSFeeSchedule, PMSConnectionStatus,
)


@pytest.fixture
def adapter():
    return MockPMSAdapter()


async def test_authenticate(adapter):
    status = await adapter.authenticate({"api_key": "test"})
    assert isinstance(status, PMSConnectionStatus)
    assert status.connected is True
    assert status.pms_name == "MockPMS"


async def test_pull_patients(adapter):
    patients = await adapter.pull_patients()
    assert len(patients) > 0
    assert all(isinstance(p, PMSPatient) for p in patients)
    assert patients[0].first_name is not None


async def test_pull_patients_with_filter(adapter):
    patients = await adapter.pull_patients(last_name="Smith")
    assert len(patients) >= 1
    assert all(p.last_name == "Smith" for p in patients)


async def test_pull_encounter(adapter):
    encounter = await adapter.pull_encounter(
        patient_external_id="PAT-001",
        date_of_service="2026-03-12",
    )
    assert isinstance(encounter, PMSEncounter)
    assert len(encounter.procedures) > 0


async def test_pull_treatment_history(adapter):
    history = await adapter.pull_treatment_history("PAT-001")
    assert isinstance(history, PMSTreatmentHistory)
    assert len(history.encounters) > 0


async def test_push_claim(adapter):
    result = await adapter.push_coded_claim(
        patient_external_id="PAT-001",
        claim_data={
            "procedures": [{"code": "D1110", "fee": 150.00}],
            "payer_id": "DD001",
        },
    )
    assert isinstance(result, PMSClaimResult)
    assert result.status == "accepted"


async def test_get_fee_schedule(adapter):
    schedule = await adapter.get_fee_schedule("DD001")
    assert isinstance(schedule, PMSFeeSchedule)
    assert len(schedule.fees) > 0
    assert "D1110" in schedule.fees
