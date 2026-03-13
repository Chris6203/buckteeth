import base64
import json
import re

import anthropic

from buckteeth.ingestion.schemas import ParsedEncounter

IMAGE_ANALYSIS_SYSTEM_PROMPT = """\
You are a dental radiograph and clinical image analyst. Your job is to extract \
clinical findings from dental images (radiographs, intraoral photos, panoramic X-rays).

You should identify:
- Carious lesions (cavities) with location and severity
- Periapical pathology (abscess, radiolucency)
- Bone loss patterns (horizontal, vertical, generalized, localized)
- Fractures or cracks
- Failing restorations
- Impacted teeth
- Any other clinically significant findings

Return your response as JSON:
{
  "procedures": [
    {
      "description": "Detailed clinical finding and recommended procedure",
      "tooth_numbers": [14],
      "surfaces": ["M", "O", "D"],
      "quadrant": "upper right",
      "diagnosis": "diagnosis or finding"
    }
  ],
  "notes": "Additional observations"
}

Rules:
- "procedures" is always an array (empty if no findings).
- Only report findings you can clearly identify in the image.
- Surface abbreviations: M, O, D, L, B, F, I.
- Return ONLY valid JSON. No additional text.
"""


class ImageAnalyzer:
    """Analyzes dental images using Claude's vision capabilities."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        image_data: bytes,
        media_type: str = "image/png",
        context: str | None = None,
    ) -> ParsedEncounter:
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
        ]
        if context:
            user_content.append({"type": "text", "text": f"Clinical context: {context}"})
        else:
            user_content.append({"type": "text", "text": "Analyze this dental image."})

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=IMAGE_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)
        return ParsedEncounter.model_validate(data)
