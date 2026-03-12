import pytest

from buckteeth.submission.adapters import MockClearinghouseAdapter


@pytest.fixture
def adapter():
    return MockClearinghouseAdapter()


async def test_submit_claim(adapter):
    result = await adapter.submit_claim({"procedure": "D2740", "fee": 1200.00})

    assert result.tracking_id is not None
    assert result.tracking_id.startswith("TRK-")
    assert result.status == "accepted"
    assert result.confirmation_number is not None
    assert result.error_message is None


async def test_check_status(adapter):
    result = await adapter.submit_claim({"procedure": "D2740", "fee": 1200.00})

    status = await adapter.check_status(result.tracking_id)

    assert status.tracking_id == result.tracking_id
    assert status.status == "accepted"
    assert status.details is not None


async def test_check_eligibility(adapter):
    result = await adapter.check_eligibility(
        patient_id="PAT-001",
        payer_id="DD001",
        subscriber_id="SUB123456",
        date_of_service="2026-03-12",
    )

    assert result.eligible is True
    assert result.annual_maximum == 2000.0
    assert result.annual_used == 450.0
    assert result.annual_remaining == 1550.0
    assert result.deductible == 50.0
    assert result.deductible_met is True
    assert result.coverage_details is not None
    assert result.coverage_details["patient_id"] == "PAT-001"
