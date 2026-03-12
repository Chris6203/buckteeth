"""Coding engine orchestrator.

Ties together the CDT code selector and validators to produce a
complete CodingResult for a parsed encounter.
"""

from __future__ import annotations

from buckteeth.coding.cdt_selector import CDTCodeSelector
from buckteeth.coding.schemas import CodingResult
from buckteeth.coding.validators import CodingValidator
from buckteeth.ingestion.schemas import ParsedEncounter


class CodingEngine:
    """Orchestrates CDT code selection and validation for an encounter."""

    def __init__(self, api_key: str) -> None:
        self._selector = CDTCodeSelector(api_key=api_key)
        self._validator = CodingValidator()

    async def code_encounter(
        self,
        encounter: ParsedEncounter,
        payer_id: str = "default",
        months_since_last: dict[str, int] | None = None,
    ) -> CodingResult:
        """Produce coding suggestions for every procedure in an encounter."""
        all_suggestions = []

        # Step 1: Select codes for each procedure
        for procedure in encounter.procedures:
            suggestions = await self._selector.select_codes(procedure)
            all_suggestions.extend(suggestions)

        # Step 2: Collect all codes for bundling checks
        all_codes = [s.cdt_code for s in all_suggestions]

        # Step 3: Validate each suggestion
        validated = []
        for suggestion in all_suggestions:
            other_codes = [c for c in all_codes if c != suggestion.cdt_code]
            result = self._validator.validate(
                suggestion,
                payer_id=payer_id,
                months_since_last=months_since_last,
                other_codes_in_encounter=other_codes,
            )
            validated.append(result)

        return CodingResult(
            suggestions=validated,
            encounter_notes=encounter.notes,
        )
