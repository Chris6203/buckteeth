import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure


@pytest.fixture
def parser():
    return ClinicalNoteParser(api_key="test-key")


def _mock_claude_response(parsed: ParsedEncounter) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = parsed.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_parse_simple_note(parser):
    expected = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="MOD composite restoration",
                tooth_numbers=[14],
                surfaces=["M", "O", "D"],
                diagnosis="recurrent decay",
            )
        ]
    )
    with patch.object(
        parser._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("MOD composite #14, recurrent decay")
        assert len(result.procedures) == 1
        assert result.procedures[0].tooth_numbers == [14]
        assert result.procedures[0].surfaces == ["M", "O", "D"]


async def test_parse_multiple_procedures(parser):
    expected = ParsedEncounter(
        procedures=[
            ParsedProcedure(description="Prophylaxis adult"),
            ParsedProcedure(description="Four bitewing radiographs"),
            ParsedProcedure(description="Periodic oral evaluation"),
        ]
    )
    with patch.object(
        parser._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("Adult prophy, 4BWX, periodic eval")
        assert len(result.procedures) == 3


async def test_parse_returns_empty_on_no_procedures(parser):
    expected = ParsedEncounter(procedures=[])
    with patch.object(
        parser._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("Patient presented for consultation only")
        assert len(result.procedures) == 0


async def test_parse_handles_markdown_code_block(parser):
    """Verify that markdown ```json wrapping is stripped correctly."""
    expected = ParsedEncounter(
        procedures=[
            ParsedProcedure(description="Extraction", tooth_numbers=[32]),
        ]
    )
    mock_block = MagicMock()
    mock_block.text = "```json\n" + expected.model_dump_json() + "\n```"
    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        parser._client.messages,
        "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await parser.parse("ext #32")
        assert len(result.procedures) == 1
        assert result.procedures[0].tooth_numbers == [32]
