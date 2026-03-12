"""Claude-powered CDT code selector using RAG.

Retrieves candidate CDT codes from the knowledge base, sends them along
with the procedure context to Claude, and returns scored suggestions.
"""

from __future__ import annotations

import json

import anthropic

from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.ingestion.schemas import ParsedProcedure
from buckteeth.knowledge.cdt_codes import CDTCodeRepository

_SYSTEM_PROMPT = """\
You are a dental coding expert. Given a clinical procedure description and \
a list of candidate CDT codes, select the most appropriate code(s).

CDT coding rules:
- Composite (resin-based) restorations are coded by number of surfaces and \
  tooth position (anterior vs posterior).
- Anterior teeth: 6-11 (upper) and 22-27 (lower).
- Posterior teeth: 1-5, 12-16 (upper) and 17-21, 28-32 (lower).
- Surface abbreviations: M=mesial, O=occlusal, D=distal, B=buccal/facial, \
  L=lingual. Count unique surfaces for composite codes.
- Crowns are coded by material (ceramic, PFM, full cast metal).
- Prophylaxis: D1110 for adults (14+), D1120 for children (<14).
- SRP is coded per quadrant, by tooth count (1-3 teeth vs 4+ teeth).

Respond ONLY with valid JSON in this format:
{
  "suggestions": [
    {
      "cdt_code": "DXXXX",
      "cdt_description": "...",
      "tooth_number": "14" or null,
      "surfaces": "MOD" or null,
      "quadrant": "UR" or null,
      "confidence_score": 0-100,
      "ai_reasoning": "Brief explanation"
    }
  ]
}
"""


class CDTCodeSelector:
    """Selects CDT codes for a parsed procedure using Claude + RAG."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._cdt_repo = CDTCodeRepository()

    async def select_codes(
        self, procedure: ParsedProcedure
    ) -> list[CodeSuggestion]:
        """Select CDT codes for a single parsed procedure."""
        candidates = self._cdt_repo.get_candidates(procedure.description)

        candidate_text = "\n".join(
            f"- {c.code}: {c.description} (category: {c.category}, "
            f"scenarios: {', '.join(c.common_scenarios)})"
            for c in candidates
        )

        user_message = (
            f"Procedure: {procedure.description}\n"
            f"Tooth numbers: {procedure.tooth_numbers}\n"
            f"Surfaces: {procedure.surfaces}\n"
            f"Quadrant: {procedure.quadrant}\n"
            f"Diagnosis: {procedure.diagnosis}\n\n"
            f"Candidate CDT codes:\n{candidate_text}"
        )

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        data = json.loads(raw)

        return [
            CodeSuggestion(**s)
            for s in data["suggestions"]
        ]
