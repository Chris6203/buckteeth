from buckteeth.coding.validators import CodingValidator
from buckteeth.coding.schemas import CodeSuggestion


def test_flag_frequency_violation():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D1110", cdt_description="Prophylaxis - adult",
        confidence_score=95, ai_reasoning="routine cleaning",
    )
    result = validator.validate(suggestion, payer_id="delta_dental", months_since_last={"D1110": 3})
    assert "frequency_concern" in result.flags


def test_no_flag_when_frequency_ok():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D1110", cdt_description="Prophylaxis - adult",
        confidence_score=95, ai_reasoning="routine cleaning",
    )
    result = validator.validate(suggestion, payer_id="delta_dental", months_since_last={"D1110": 7})
    assert "frequency_concern" not in result.flags


def test_flag_bundling_risk():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D2950", cdt_description="Core buildup",
        confidence_score=90, ai_reasoning="buildup needed",
    )
    result = validator.validate(suggestion, payer_id="delta_dental", other_codes_in_encounter=["D2740"])
    assert "bundling_risk" in result.flags


def test_flag_low_confidence():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D7210", cdt_description="Surgical extraction",
        confidence_score=65, ai_reasoning="might need surgical approach",
    )
    result = validator.validate(suggestion, payer_id="delta_dental")
    assert "low_confidence" in result.flags


def test_flag_narrative_required():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D4341", cdt_description="SRP - 4+ teeth per quadrant",
        confidence_score=92, ai_reasoning="perio therapy",
    )
    result = validator.validate(suggestion, payer_id="delta_dental")
    assert "needs_narrative" in result.flags
