import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.denials.risk_scorer import DenialRiskScorer, RiskAssessment


@pytest.fixture
def scorer():
    return DenialRiskScorer(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_assess_low_risk(scorer):
    mock_text = '{"risk_score": 15, "risk_level": "low", "risk_factors": [], "recommendations": ["Claim looks routine, proceed with submission"]}'
    with patch.object(scorer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await scorer.assess(
            cdt_codes=["D1110"],
            payer_name="Delta Dental",
            payer_id="DD001",
            patient_age=35,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Routine prophylaxis, healthy patient",
        )
        assert isinstance(result, RiskAssessment)
        assert result.risk_score <= 30
        assert result.risk_level == "low"


async def test_assess_high_risk(scorer):
    mock_text = '{"risk_score": 78, "risk_level": "high", "risk_factors": ["Crown frequency limit: last crown on this tooth within 5 years", "Missing pre-authorization for major procedure", "Payer frequently denies D2740 without radiographic evidence"], "recommendations": ["Obtain pre-authorization before submission", "Attach periapical radiograph showing clinical necessity", "Include detailed clinical narrative"]}'
    with patch.object(scorer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await scorer.assess(
            cdt_codes=["D2740"],
            payer_name="MetLife",
            payer_id="ML001",
            patient_age=45,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Crown on #30, previous crown 3 years ago",
        )
        assert result.risk_score >= 60
        assert result.risk_level == "high"
        assert len(result.risk_factors) > 0
        assert len(result.recommendations) > 0


def test_rule_based_frequency_check(scorer):
    factors = scorer._check_frequency_risks(
        cdt_codes=["D0274"],  # BWX - typically 1x/year
        payer_name="Delta Dental",
        last_service_dates={"D0274": "2026-01-15"},
    )
    assert len(factors) > 0  # Should flag recent BWX


def test_rule_based_no_frequency_issue(scorer):
    factors = scorer._check_frequency_risks(
        cdt_codes=["D1110"],  # Prophy - 2x/year
        payer_name="Delta Dental",
        last_service_dates={"D1110": "2025-09-01"},
    )
    assert len(factors) == 0  # 6+ months ago, should be fine
