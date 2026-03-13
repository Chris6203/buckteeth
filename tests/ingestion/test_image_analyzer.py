import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.ingestion.image_analyzer import ImageAnalyzer
from buckteeth.ingestion.schemas import ParsedEncounter


@pytest.fixture
def analyzer():
    return ImageAnalyzer(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_analyze_xray(analyzer):
    mock_text = '{"procedures": [{"description": "Periapical radiolucency at apex of tooth #19 consistent with pulpal necrosis requiring root canal therapy", "tooth_numbers": [19], "surfaces": null, "quadrant": "lower left", "diagnosis": "pulpal necrosis"}], "notes": "Radiograph shows periapical pathology"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-image-bytes",
            media_type="image/png",
            context="Patient complains of pain on lower left",
        )
        assert isinstance(result, ParsedEncounter)
        assert len(result.procedures) == 1
        assert result.procedures[0].tooth_numbers == [19]


async def test_analyze_intraoral_photo(analyzer):
    mock_text = '{"procedures": [{"description": "Large carious lesion on occlusal surface of tooth #30", "tooth_numbers": [30], "surfaces": ["O"], "quadrant": "lower right", "diagnosis": "dental caries"}], "notes": "Visible cavitation"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-photo-bytes",
            media_type="image/jpeg",
            context="Routine exam",
        )
        assert len(result.procedures) == 1
        assert "O" in result.procedures[0].surfaces


async def test_analyze_with_no_findings(analyzer):
    mock_text = '{"procedures": [], "notes": "No abnormal findings on radiograph"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-image-bytes",
            media_type="image/png",
        )
        assert len(result.procedures) == 0
        assert "no abnormal" in result.notes.lower()
