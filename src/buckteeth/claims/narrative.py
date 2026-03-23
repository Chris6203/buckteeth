"""Claude-powered clinical narrative generator for dental claims.

Generates insurance-reviewer-appropriate narratives that justify
medical necessity for dental procedures.
"""

from __future__ import annotations

import json
import re

import anthropic

from buckteeth.claims.schemas import NarrativeRequest, NarrativeResponse
from buckteeth.knowledge.cdt_codes import CDTCodeRepository

NARRATIVE_SYSTEM_PROMPT = """\
You are a dental insurance narrative specialist. Your job is to write concise \
clinical narratives that justify the medical necessity of dental procedures for \
insurance claim submissions.

Guidelines:
- Write 2-4 sentence clinical narratives.
- Use insurance-reviewer-appropriate clinical terminology.
- Reference specific clinical findings such as pocket depths, fracture lines, \
radiographic findings, bleeding on probing, mobility, etc.
- Clearly explain WHY the procedure is necessary, not just what was done.
- If a payer name is provided, tailor the language to that payer's known \
preferences and requirements.
- Return your response as JSON with exactly these fields:
  {"cdt_code": "<the CDT code>", "narrative_text": "<your narrative>", "payer_tailored": <true if payer was specified, false otherwise>}
- Return ONLY the JSON object, no other text.
"""


class NarrativeGenerator:
    """Generates clinical narratives for dental procedures using Claude."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._cdt_repo = CDTCodeRepository()

    def needs_narrative(self, cdt_code: str) -> bool:
        """Check whether a CDT code requires a clinical narrative."""
        code = self._cdt_repo.lookup(cdt_code)
        if code is None:
            return False
        return code.narrative_required

    async def generate(self, request: NarrativeRequest) -> NarrativeResponse:
        """Generate a clinical narrative for the given procedure."""
        user_prompt = self._build_user_prompt(request)

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)

        return NarrativeResponse(
            cdt_code=data["cdt_code"],
            narrative_text=data["narrative_text"],
            payer_tailored=data.get("payer_tailored", False),
        )

    @staticmethod
    def _build_user_prompt(request: NarrativeRequest) -> str:
        parts = [
            f"CDT Code: {request.cdt_code}",
            f"Procedure: {request.procedure_description}",
            f"Clinical Notes: {request.clinical_notes}",
        ]
        if request.diagnosis:
            parts.append(f"Diagnosis: {request.diagnosis}")
        if request.tooth_number:
            parts.append(f"Tooth Number: {request.tooth_number}")
        if request.surfaces:
            parts.append(f"Surfaces: {request.surfaces}")
        if request.payer_name:
            parts.append(f"Payer: {request.payer_name}")

        parts.append(
            "\nGenerate a clinical narrative justifying medical necessity."
        )
        return "\n".join(parts)
