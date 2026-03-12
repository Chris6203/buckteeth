"""Coding validators for CDT code suggestions.

Checks frequency limits, bundling risks, confidence thresholds, and
narrative requirements against payer rules and CDT code metadata.
"""

from __future__ import annotations

from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.knowledge.cdt_codes import CDTCodeRepository
from buckteeth.knowledge.payer_rules import PayerRuleRepository


class CodingValidator:
    """Validates a CodeSuggestion and adds appropriate flags."""

    def __init__(self) -> None:
        self._cdt_repo = CDTCodeRepository()
        self._payer_repo = PayerRuleRepository()

    def validate(
        self,
        suggestion: CodeSuggestion,
        payer_id: str = "default",
        months_since_last: dict[str, int] | None = None,
        other_codes_in_encounter: list[str] | None = None,
    ) -> CodeSuggestion:
        """Return a copy of the suggestion with validation flags added."""
        flags: list[str] = list(suggestion.flags)

        # frequency_concern
        if months_since_last and suggestion.cdt_code in months_since_last:
            result = self._payer_repo.check_frequency(
                payer_id, suggestion.cdt_code, months_since_last[suggestion.cdt_code]
            )
            if not result.allowed:
                flags.append("frequency_concern")

        # bundling_risk
        if other_codes_in_encounter:
            bundling_rules = self._payer_repo.get_bundling_rules(suggestion.cdt_code)
            other_set = set(c.upper().strip() for c in other_codes_in_encounter)
            for rule in bundling_rules:
                paired = rule.bundled_with if rule.code == suggestion.cdt_code else rule.code
                if paired in other_set:
                    flags.append("bundling_risk")
                    break

        # low_confidence
        if suggestion.confidence_score < 75:
            flags.append("low_confidence")

        # needs_narrative
        cdt = self._cdt_repo.lookup(suggestion.cdt_code)
        if cdt and cdt.narrative_required:
            flags.append("needs_narrative")

        return suggestion.model_copy(update={"flags": flags})
