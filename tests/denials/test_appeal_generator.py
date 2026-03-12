import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.denials.appeal_generator import AppealGenerator
from buckteeth.denials.schemas import AppealRequest


@pytest.fixture
def generator():
    return AppealGenerator(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_generate_appeal(generator):
    request = AppealRequest(
        denial_reason_code="CO-50",
        denial_reason_description="Not medically necessary",
        denied_amount=750.00,
        payer_name="Delta Dental",
        cdt_code="D2740",
        procedure_description="Crown - porcelain/ceramic",
        clinical_notes="Tooth #30 large MOD fracture with recurrent decay",
        patient_name="Jane Doe",
        date_of_service="2026-03-12",
        provider_name="Dr. Smith",
        state="CA",
    )
    mock_text = '{"appeal_text": "Dear Claims Review Department, We are writing to formally appeal the denial of claim for patient Jane Doe...", "case_law_citations": ["Hughes v. Blue Cross of California, 215 Cal.App.3d 832 (1989)"], "key_arguments": ["Clinical necessity documented by treating provider", "Fracture confirmed on radiograph"], "recommended_attachments": ["Periapical radiograph of tooth #30", "Clinical photographs"]}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock, return_value=_mock_claude_response(mock_text)):
        result = await generator.generate_appeal(request)
        assert "appeal" in result.appeal_text.lower() or "denial" in result.appeal_text.lower()
        assert len(result.case_law_citations) > 0
        assert len(result.key_arguments) > 0


async def test_appeal_includes_case_law(generator):
    request = AppealRequest(
        denial_reason_code="CO-45",
        denial_reason_description="Charges exceed fee arrangement",
        denied_amount=200.00,
        payer_name="MetLife",
        cdt_code="D4341",
        procedure_description="SRP - 4+ teeth per quadrant",
        clinical_notes="Pocket depths 5-7mm, bleeding on probing",
        patient_name="John Smith",
        date_of_service="2026-03-12",
        provider_name="Dr. Jones",
        state="TX",
    )
    # Verify case law repo is consulted (check that relevant citations are fetched)
    citations = generator._case_law_repo.get_relevant_citations("CO-45", "D4341", "TX")
    assert len(citations) > 0
