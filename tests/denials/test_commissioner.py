import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.denials.commissioner import CommissionerLetterGenerator
from buckteeth.denials.schemas import CommissionerLetterRequest


@pytest.fixture
def generator():
    return CommissionerLetterGenerator(api_key="test-key")


async def test_generate_commissioner_letter(generator):
    request = CommissionerLetterRequest(
        denial_reason_code="CO-50",
        denial_reason_description="Not medically necessary",
        denied_amount=750.00,
        payer_name="Delta Dental",
        patient_name="Jane Doe",
        patient_address="123 Main St, Los Angeles, CA 90001",
        provider_name="Dr. Smith",
        provider_address="456 Dental Ave, Los Angeles, CA 90002",
        date_of_service="2026-03-12",
        cdt_code="D2740",
        procedure_description="Crown - porcelain/ceramic",
        clinical_notes="Tooth #30 large MOD fracture with recurrent decay",
        state="CA",
    )
    mock_text = '{"letter_text": "Dear Commissioner, I am writing to file a formal complaint...", "commissioner_name": "California Department of Insurance", "commissioner_address": "300 Capitol Mall, Suite 1700, Sacramento, CA 95814", "case_law_citations": ["Hughes v. Blue Cross of California (1989)"], "regulatory_citations": ["California Insurance Code § 10123.135"]}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock, return_value=MagicMock(content=[MagicMock(text=mock_text)])):
        result = await generator.generate(request)
        assert "commissioner" in result.letter_text.lower() or "complaint" in result.letter_text.lower()
        assert result.commissioner_name is not None
        assert result.commissioner_address is not None
        assert len(result.case_law_citations) > 0


def test_get_commissioner_info(generator):
    info = generator.get_commissioner_info("CA")
    assert info["name"] is not None
    assert info["address"] is not None

    info_tx = generator.get_commissioner_info("TX")
    assert info_tx["name"] is not None
