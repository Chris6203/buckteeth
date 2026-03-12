"""Claude-powered appeal letter generator for denied dental insurance claims.

Generates formal appeal letters citing relevant case law and regulatory
references to challenge insurance claim denials.
"""

from __future__ import annotations

import json

import anthropic

from buckteeth.knowledge.case_law import CaseLawRepository
from buckteeth.denials.schemas import AppealRequest, AppealResponse

APPEAL_SYSTEM_PROMPT = """\
You are a dental insurance appeals specialist and healthcare attorney. Your job is to write \
formal appeal letters for denied dental insurance claims.

Guidelines:
- Write professional, formal appeal letters suitable for submission to insurance companies.
- Reference specific case law, regulatory citations, and ADA guidelines provided.
- Cite clinical evidence from the treating provider's notes.
- Explain why the denial is incorrect based on the patient's clinical presentation.
- Include specific legal and regulatory arguments.
- Return your response as JSON with these fields:
  {"appeal_text": "<full appeal letter>", "case_law_citations": ["<list of citations used>"], "key_arguments": ["<list of key arguments>"], "recommended_attachments": ["<list of recommended supporting documents>"]}
- Return ONLY the JSON object, no other text.
"""


class AppealGenerator:
    """Generates formal appeal letters for denied dental insurance claims using Claude."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._case_law_repo = CaseLawRepository()

    async def generate_appeal(self, request: AppealRequest) -> AppealResponse:
        """Generate a formal appeal letter for the given denial."""
        # 1. Get relevant case law
        citations = self._case_law_repo.get_relevant_citations(
            denial_code=request.denial_reason_code,
            procedure_code=request.cdt_code,
            state=request.state,
        )

        # 2. Build prompt with case law context
        user_prompt = self._build_prompt(request, citations)

        # 3. Call Claude
        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=APPEAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # 4. Parse response
        raw_text = response.content[0].text
        data = json.loads(raw_text)

        return AppealResponse(
            appeal_text=data["appeal_text"],
            case_law_citations=data["case_law_citations"],
            key_arguments=data["key_arguments"],
            recommended_attachments=data.get("recommended_attachments", []),
        )

    @staticmethod
    def _build_prompt(request: AppealRequest, citations) -> str:
        """Build the user prompt with denial details and relevant case law."""
        # Build case law context
        case_law_text = ""
        for c in citations[:5]:  # top 5 most relevant
            case_law_text += f"\n- {c.citation}: {c.key_principle}"

        return f"""Denial Details:
- Patient: {request.patient_name}
- Provider: {request.provider_name}
- Date of Service: {request.date_of_service}
- CDT Code: {request.cdt_code} - {request.procedure_description}
- Denial Reason: {request.denial_reason_code} - {request.denial_reason_description}
- Denied Amount: ${request.denied_amount:.2f}
- Payer: {request.payer_name}
- State: {request.state}

Clinical Notes:
{request.clinical_notes}

Relevant Case Law and Regulations:
{case_law_text}

Generate a formal appeal letter citing the above case law and clinical evidence."""
