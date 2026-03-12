"""Tests for the claim builder orchestrator."""

import pytest
from unittest.mock import AsyncMock, patch

from buckteeth.claims.builder import ClaimBuilder
from buckteeth.claims.schemas import NarrativeResponse
from buckteeth.coding.schemas import CodeSuggestion


@pytest.fixture
def builder():
    return ClaimBuilder(api_key="test-key")


@pytest.mark.asyncio
async def test_build_claim_with_narrative(builder):
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D4341",
            cdt_description="SRP - 4+ teeth per quadrant",
            quadrant="UR",
            confidence_score=95,
            ai_reasoning="SRP needed",
            flags=["needs_narrative"],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    mock_narrative = NarrativeResponse(
        cdt_code="D4341",
        narrative_text="Patient presents with generalized moderate periodontitis...",
        payer_tailored=True,
    )
    with patch.object(
        builder._narrative_gen,
        "generate",
        new_callable=AsyncMock,
        return_value=mock_narrative,
    ):
        result = await builder.build(
            coded_procedures=coded_procedures,
            patient_info=patient_info,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Pocket depths 5-7mm UR",
        )
        assert len(result.procedures) == 1
        assert result.procedures[0].narrative is not None
        assert result.primary_payer_name == "Delta Dental"
        assert result.has_narratives is True


@pytest.mark.asyncio
async def test_build_claim_without_narrative(builder):
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D1110",
            cdt_description="Prophylaxis - adult",
            confidence_score=99,
            ai_reasoning="Standard prophy",
            flags=[],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Routine cleaning",
    )
    assert len(result.procedures) == 1
    assert result.procedures[0].narrative is None
    assert result.has_narratives is False


@pytest.mark.asyncio
async def test_build_claim_multiple_procedures(builder):
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D0120",
            cdt_description="Periodic eval",
            confidence_score=99,
            ai_reasoning="Exam",
            flags=[],
        ),
        CodeSuggestion(
            cdt_code="D1110",
            cdt_description="Prophylaxis - adult",
            confidence_score=99,
            ai_reasoning="Cleaning",
            flags=[],
        ),
        CodeSuggestion(
            cdt_code="D0274",
            cdt_description="Bitewings - four",
            confidence_score=99,
            ai_reasoning="BWX",
            flags=[],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Routine visit",
    )
    assert len(result.procedures) == 3
    assert result.procedure_count == 3


@pytest.mark.asyncio
async def test_build_claim_preauth_required(builder):
    """Crown codes should trigger preauth_required flag."""
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D2750",
            cdt_description="Crown - porcelain fused to high noble metal",
            tooth_number="14",
            confidence_score=95,
            ai_reasoning="Crown needed",
            flags=[],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Fractured tooth #14",
    )
    assert result.preauth_required is True
    assert result.has_preauth is True


@pytest.mark.asyncio
async def test_build_claim_no_preauth_for_routine(builder):
    """Routine codes should not trigger preauth."""
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D1110",
            cdt_description="Prophylaxis - adult",
            confidence_score=99,
            ai_reasoning="Cleaning",
            flags=[],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Routine cleaning",
    )
    assert result.preauth_required is False
    assert result.has_preauth is False
