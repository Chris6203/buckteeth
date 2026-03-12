import uuid

import pytest

from buckteeth.submission.adapters import MockClearinghouseAdapter
from buckteeth.submission.gateway import SubmissionGateway


@pytest.fixture
def gateway():
    adapter = MockClearinghouseAdapter()
    return SubmissionGateway(adapter)


async def test_submit_claim(gateway):
    claim_id = uuid.uuid4()
    result = await gateway.submit(claim_id, {"procedure": "D2740", "fee": 1200.00})

    assert result.tracking_id is not None
    assert result.status == "accepted"
    assert result.confirmation_number is not None


async def test_submit_with_idempotency(gateway):
    claim_id = uuid.uuid4()
    key = "idem-key-001"

    result1 = await gateway.submit(
        claim_id, {"procedure": "D2740", "fee": 1200.00}, idempotency_key=key
    )
    result2 = await gateway.submit(
        claim_id, {"procedure": "D2740", "fee": 1200.00}, idempotency_key=key
    )

    assert result1.tracking_id == result2.tracking_id
    assert result1.confirmation_number == result2.confirmation_number


async def test_check_status(gateway):
    claim_id = uuid.uuid4()
    result = await gateway.submit(claim_id, {"procedure": "D2740", "fee": 1200.00})

    status = await gateway.check_status(result.tracking_id)

    assert status.tracking_id == result.tracking_id
    assert status.status == "accepted"


async def test_batch_submit(gateway):
    claims = [
        (uuid.uuid4(), {"procedure": "D2740", "fee": 1200.00}),
        (uuid.uuid4(), {"procedure": "D0120", "fee": 50.00}),
        (uuid.uuid4(), {"procedure": "D1110", "fee": 150.00}),
    ]

    results = await gateway.batch_submit(claims)

    assert len(results) == 3
    tracking_ids = [r.tracking_id for r in results]
    assert len(set(tracking_ids)) == 3  # all unique
    for result in results:
        assert result.status == "accepted"
        assert result.tracking_id.startswith("TRK-")
