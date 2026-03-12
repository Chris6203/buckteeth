"""Claim builder orchestrator.

Takes coded procedures and patient info and assembles a complete claim
with narratives generated where needed.
"""

from __future__ import annotations

import uuid

from buckteeth.claims.narrative import NarrativeGenerator
from buckteeth.claims.schemas import (
    ClaimDetail,
    ClaimProcedureDetail,
    NarrativeRequest,
    NarrativeResponse,
)
from buckteeth.coding.schemas import CodeSuggestion

PREAUTH_CODES = {"D2740", "D2750", "D5110", "D5120"}


class ClaimBuilder:
    """Assembles a complete dental claim from coded procedures and patient info."""

    def __init__(self, api_key: str) -> None:
        self._narrative_gen = NarrativeGenerator(api_key=api_key)

    async def build(
        self,
        coded_procedures: list[CodeSuggestion],
        patient_info: dict,
        provider_name: str,
        date_of_service: str,
        clinical_notes: str,
    ) -> ClaimDetail:
        """Build a complete claim with narratives for procedures that need them."""
        procedures: list[ClaimProcedureDetail] = []
        narratives: list[NarrativeResponse] = []
        preauth_required = False

        for proc in coded_procedures:
            narrative: NarrativeResponse | None = None

            if "needs_narrative" in proc.flags:
                narrative = await self._narrative_gen.generate(
                    NarrativeRequest(
                        cdt_code=proc.cdt_code,
                        procedure_description=proc.cdt_description,
                        clinical_notes=clinical_notes,
                        tooth_number=proc.tooth_number,
                        surfaces=proc.surfaces,
                        payer_name=patient_info.get("primary_payer_name"),
                    )
                )
                narratives.append(narrative)

            if proc.cdt_code in PREAUTH_CODES:
                preauth_required = True

            procedures.append(
                ClaimProcedureDetail(
                    cdt_code=proc.cdt_code,
                    cdt_description=proc.cdt_description,
                    tooth_number=proc.tooth_number,
                    surfaces=proc.surfaces,
                    quadrant=proc.quadrant,
                    narrative=narrative,
                )
            )

        return ClaimDetail(
            claim_id=uuid.uuid4(),
            patient_name=patient_info.get("name", ""),
            provider_name=provider_name,
            date_of_service=date_of_service,
            status="draft",
            primary_payer_name=patient_info.get("primary_payer_name", ""),
            primary_subscriber_id=patient_info.get("primary_subscriber_id", ""),
            primary_group_number=patient_info.get("primary_group_number", ""),
            procedures=procedures,
            narratives=narratives,
            preauth_required=preauth_required,
            procedure_count=len(procedures),
            has_narratives=len(narratives) > 0,
            has_preauth=preauth_required,
        )
