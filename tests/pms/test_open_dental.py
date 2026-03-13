import pytest
from buckteeth.pms.open_dental import OpenDentalAdapter
from buckteeth.pms.schemas import PMSConnectionStatus


@pytest.fixture
def adapter():
    return OpenDentalAdapter(base_url="http://localhost:30222/api/v1", api_key="test-key")


async def test_authenticate_raises_not_implemented(adapter):
    """Open Dental adapter methods raise NotImplementedError until real API is configured."""
    with pytest.raises(NotImplementedError, match="Open Dental"):
        await adapter.authenticate({})


def test_adapter_stores_config(adapter):
    assert adapter._base_url == "http://localhost:30222/api/v1"
    assert adapter._api_key == "test-key"
