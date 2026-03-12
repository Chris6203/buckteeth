import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.coding.cdt_selector import CDTCodeSelector
from buckteeth.ingestion.schemas import ParsedProcedure
import json


@pytest.fixture
def selector():
    return CDTCodeSelector(api_key="test-key")


def _mock_claude_response(suggestions: list[dict]) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = json.dumps({"suggestions": suggestions})
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@pytest.mark.asyncio
async def test_select_code_for_composite(selector):
    procedure = ParsedProcedure(
        description="MOD composite restoration",
        tooth_numbers=[14], surfaces=["M", "O", "D"],
        diagnosis="recurrent decay",
    )
    mock_response = _mock_claude_response([{
        "cdt_code": "D2393",
        "cdt_description": "Resin-based composite - three surfaces, posterior",
        "tooth_number": "14", "surfaces": "MOD",
        "confidence_score": 97,
        "ai_reasoning": "Three-surface (MOD) composite on posterior tooth #14",
    }])
    with patch.object(selector._client.messages, "create",
                      new_callable=AsyncMock, return_value=mock_response):
        results = await selector.select_codes(procedure)
        assert len(results) == 1
        assert results[0].cdt_code == "D2393"


@pytest.mark.asyncio
async def test_select_code_for_prophy(selector):
    procedure = ParsedProcedure(description="Adult prophylaxis")
    mock_response = _mock_claude_response([{
        "cdt_code": "D1110",
        "cdt_description": "Prophylaxis - adult",
        "confidence_score": 99,
        "ai_reasoning": "Standard adult prophylaxis",
    }])
    with patch.object(selector._client.messages, "create",
                      new_callable=AsyncMock, return_value=mock_response):
        results = await selector.select_codes(procedure)
        assert len(results) == 1
        assert results[0].cdt_code == "D1110"
