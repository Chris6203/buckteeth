import pytest
from unittest.mock import AsyncMock, patch
from buckteeth.coding.engine import CodingEngine
from buckteeth.coding.schemas import CodeSuggestion, CodingResult
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure


@pytest.fixture
def engine():
    return CodingEngine(api_key="test-key")


@pytest.mark.asyncio
async def test_code_encounter_end_to_end(engine):
    encounter = ParsedEncounter(
        procedures=[
            ParsedProcedure(description="MOD composite restoration",
                tooth_numbers=[14], surfaces=["M", "O", "D"], diagnosis="recurrent decay"),
            ParsedProcedure(description="Adult prophylaxis"),
        ]
    )
    mock_suggestions_1 = [CodeSuggestion(
        cdt_code="D2393", cdt_description="Resin-based composite - three surfaces, posterior",
        tooth_number="14", surfaces="MOD", confidence_score=97,
        ai_reasoning="MOD composite on posterior tooth #14",
    )]
    mock_suggestions_2 = [CodeSuggestion(
        cdt_code="D1110", cdt_description="Prophylaxis - adult",
        confidence_score=99, ai_reasoning="Standard adult prophylaxis",
    )]
    with patch.object(engine._selector, "select_codes",
                      new_callable=AsyncMock, side_effect=[mock_suggestions_1, mock_suggestions_2]):
        result = await engine.code_encounter(encounter, payer_id="delta_dental")
        assert len(result.suggestions) == 2
        codes = [s.cdt_code for s in result.suggestions]
        assert "D2393" in codes
        assert "D1110" in codes


@pytest.mark.asyncio
async def test_code_encounter_adds_validation_flags(engine):
    encounter = ParsedEncounter(
        procedures=[ParsedProcedure(description="SRP four teeth upper right quadrant")]
    )
    mock_suggestions = [CodeSuggestion(
        cdt_code="D4341", cdt_description="SRP - four or more teeth per quadrant",
        quadrant="UR", confidence_score=92, ai_reasoning="SRP on UR quadrant",
    )]
    with patch.object(engine._selector, "select_codes",
                      new_callable=AsyncMock, return_value=mock_suggestions):
        result = await engine.code_encounter(encounter, payer_id="delta_dental")
        assert "needs_narrative" in result.suggestions[0].flags
