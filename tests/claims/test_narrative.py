import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.claims.narrative import NarrativeGenerator
from buckteeth.claims.schemas import NarrativeRequest


@pytest.fixture
def generator():
    return NarrativeGenerator(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_generate_srp_narrative(generator):
    request = NarrativeRequest(
        cdt_code="D4341",
        procedure_description="SRP - 4+ teeth, UR quadrant",
        clinical_notes="Pocket depths 5-7mm UR. Bleeding on probing. Subgingular calculus.",
        diagnosis="Generalized moderate periodontitis",
        payer_name="Delta Dental",
    )
    mock_text = '{"cdt_code": "D4341", "narrative_text": "Patient presents with generalized moderate periodontitis with probing depths of 5-7mm in the upper right quadrant. Bleeding on probing and subgingival calculus were noted. Scaling and root planing is necessary to remove bacterial deposits and promote tissue healing.", "payer_tailored": true}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock, return_value=_mock_claude_response(mock_text)):
        result = await generator.generate(request)
        assert result.cdt_code == "D4341"
        assert "periodontitis" in result.narrative_text.lower()
        assert result.payer_tailored is True


async def test_generate_crown_narrative(generator):
    request = NarrativeRequest(
        cdt_code="D2740",
        procedure_description="Crown - porcelain/ceramic",
        clinical_notes="Tooth #30 large MOD amalgam with recurrent decay and mesial ridge fracture.",
        diagnosis="Fractured tooth with recurrent decay",
        tooth_number="30",
    )
    mock_text = '{"cdt_code": "D2740", "narrative_text": "Tooth #30 presents with a large MOD amalgam with recurrent decay and mesial marginal ridge fracture. Remaining structure insufficient for direct restoration. Crown recommended.", "payer_tailored": false}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock, return_value=_mock_claude_response(mock_text)):
        result = await generator.generate(request)
        assert result.cdt_code == "D2740"
        assert "crown" in result.narrative_text.lower()


async def test_needs_narrative_check(generator):
    assert generator.needs_narrative("D4341") is True   # SRP
    assert generator.needs_narrative("D2740") is True   # Crown
    assert generator.needs_narrative("D1110") is False  # Prophy
    assert generator.needs_narrative("D0120") is False  # Periodic eval
