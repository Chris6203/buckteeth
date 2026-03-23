import json
import re

import anthropic

from buckteeth.ingestion.schemas import ParsedEncounter


SYSTEM_PROMPT = """\
You are a dental clinical note parser. Your job is to extract structured procedure \
data from free-text clinical notes.

Dental terminology and common abbreviations:
- MOD, MO, DO, OL, etc. = tooth surfaces (Mesial, Occlusal, Distal, Lingual, Buccal, Facial)
- comp / composite = tooth-colored filling material
- prophy = prophylaxis (dental cleaning)
- BWX = bitewing radiographs (X-rays)
- FMX = full-mouth radiograph series
- PA = periapical radiograph
- SRP = scaling and root planing (deep cleaning)
- RCT = root canal therapy
- ext = extraction
- # = tooth number (e.g. #14 means tooth number 14)

IMPORTANT clinical billing rules:
- A "routine recall visit" or "recall exam" ALWAYS includes a periodic oral evaluation \
  (D0120) even if not explicitly stated. Always include the evaluation as a procedure.
- "Child patient" or patient under age 14 gets D1120 (child prophy), NOT D1110 (adult).
- For extractions: if the notes say "extracted in one piece" or describe a simple \
  forceps extraction with NO bone removal, NO flap, NO sectioning, this is D7140 (simple). \
  Only code D7210 (surgical) if the notes explicitly mention bone removal, flap, or sectioning.
- A crown impression/final impression is part of the crown prep procedure — do NOT code \
  it separately as diagnostic casts (D0470) unless the notes specifically say "diagnostic casts."
- Do NOT duplicate procedures. If core buildup is mentioned once, list it once even if \
  the crown prep notes mention the tooth condition twice.

Return your response as JSON with the following structure:
{
  "procedures": [
    {
      "description": "Human-readable procedure description",
      "tooth_numbers": [14],
      "surfaces": ["M", "O", "D"],
      "quadrant": "upper right",
      "diagnosis": "recurrent decay"
    }
  ],
  "notes": "Any additional notes or observations"
}

Rules:
- "procedures" is always an array (may be empty if no procedures found).
- IMPORTANT: Each billable procedure must be a SEPARATE entry. For example, \
  "crown prep with core buildup" should be TWO procedures: one for the core \
  buildup and one for the crown preparation. Similarly, "prophy and BWX" \
  should be TWO procedures. Each line item on an insurance claim is a separate procedure.
- Common procedure splits: crown + core buildup, extraction + bone graft, \
  evaluation + radiographs, prophy + fluoride, SRP + irrigation.
- "tooth_numbers", "surfaces", "quadrant", and "diagnosis" are optional (use null if not applicable).
- Surface abbreviations should be single uppercase letters: M, O, D, L, B, F, I.
- Return ONLY valid JSON. No additional text or explanation.
"""


class ClinicalNoteParser:
    """Parses free-text clinical notes into structured procedure data using Claude."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def parse(self, clinical_notes: str) -> ParsedEncounter:
        """Parse clinical notes into a structured ParsedEncounter."""
        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": clinical_notes},
            ],
        )

        raw_text = response.content[0].text

        # Strip markdown code block wrapping if present
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

        data = json.loads(cleaned)
        return ParsedEncounter.model_validate(data)
