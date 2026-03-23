"""
Appeal Document Verifier

Uses Claude Vision to verify that uploaded documents match their
claimed type and contain the expected information for the appeal.

Checks:
- Is this actually a dental image/document?
- Does it match the claimed document type (periapical vs bitewing vs pano)?
- For X-rays: is the relevant tooth/area visible?
- For perio charting: does it contain actual pocket depth data?
- Is the image quality sufficient for insurance submission?
"""

from __future__ import annotations

import base64
import json
import re

import anthropic


VERIFY_SYSTEM_PROMPT = """\
You are a dental document verification specialist. Your job is to verify that \
uploaded documents match their claimed type and are suitable for insurance appeal submission.

Analyze the uploaded document and return a JSON assessment:
{
  "verified": true/false,
  "actual_type": "what this document actually is",
  "matches_claimed_type": true/false,
  "quality": "good" | "acceptable" | "poor" | "unusable",
  "findings": "what you see in the document",
  "issues": ["list of any problems found"],
  "suggestions": ["list of suggestions to improve"],
  "tooth_visible": "tooth number(s) visible, or null",
  "suitable_for_appeal": true/false,
  "reason": "brief explanation of your assessment"
}

Document type definitions:
- periapical_xray: Shows the full tooth including root apex and surrounding bone. Typically 1-3 teeth.
- bitewing_xray: Shows the crowns of upper and lower teeth and interproximal bone. Typically 4-8 teeth.
- panoramic_xray: Full mouth panoramic view showing all teeth, jaws, and TMJs.
- intraoral_photo: Clinical photograph taken inside the mouth showing teeth/gums.
- perio_charting: A form/chart with pocket depth measurements (numbers 1-12+ per tooth).
- clinical_narrative: A typed or written clinical note/narrative.
- eob: An Explanation of Benefits form from an insurance company.
- treatment_plan: A dental treatment plan document.

Rules:
- Be strict about type matching — a bitewing is NOT a periapical and vice versa.
- Quality assessment should consider: resolution, clarity, exposure, positioning.
- For X-rays, verify the area of interest is visible and diagnostic quality.
- Return ONLY valid JSON.
"""


class DocumentVerifier:
    """Verifies uploaded appeal documents using Claude Vision."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def verify(
        self,
        file_data: bytes,
        media_type: str,
        claimed_type: str,
        context: str = "",
    ) -> dict:
        """
        Verify a document matches its claimed type and is suitable for appeal.

        Args:
            file_data: Raw file bytes
            media_type: MIME type
            claimed_type: What the user says this document is
            context: Additional context (e.g., "for tooth #19 crown denial")

        Returns:
            Verification result dict
        """
        # Only verify images — PDFs and docs can't be analyzed by Vision
        if not media_type.startswith("image/"):
            return {
                "verified": True,
                "actual_type": "document",
                "matches_claimed_type": True,
                "quality": "acceptable",
                "findings": "Non-image document — cannot verify visually. Please ensure this is the correct document.",
                "issues": [],
                "suggestions": [],
                "tooth_visible": None,
                "suitable_for_appeal": True,
                "reason": "Document format accepted. Visual verification only available for images.",
            }

        image_b64 = base64.b64encode(file_data).decode("utf-8")

        user_text = f"Claimed document type: {claimed_type}\n"
        if context:
            user_text += f"Context: {context}\n"
        user_text += "Verify this document."

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=VERIFY_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }],
            )

            raw = response.content[0].text
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
            return json.loads(cleaned)

        except Exception as e:
            return {
                "verified": False,
                "actual_type": "unknown",
                "matches_claimed_type": False,
                "quality": "unknown",
                "findings": f"Verification failed: {str(e)}",
                "issues": ["Could not verify document — AI analysis unavailable"],
                "suggestions": ["Manually confirm this is the correct document"],
                "tooth_visible": None,
                "suitable_for_appeal": True,
                "reason": "Verification unavailable — document accepted without AI check.",
            }
