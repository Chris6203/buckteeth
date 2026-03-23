from __future__ import annotations

"""
Image-Procedure Verification Module

Uses Claude Vision to verify that dental images (X-rays, radiographs, photos)
support the coded procedures. Flags mismatches, missing evidence, and
potential missed findings.

This is critical for:
- Preventing claim denials due to lack of radiographic evidence
- Catching coding errors before submission
- Identifying missed billable procedures visible in images
- Building stronger documentation for appeals
"""

import base64
import json
import re

import anthropic

VERIFICATION_SYSTEM_PROMPT = """\
You are a dental insurance claim verification specialist. Your job is to compare \
dental images (radiographs, X-rays, intraoral photos) against a list of coded \
procedures and determine whether the images support the procedures being billed.

For each coded procedure, evaluate:
1. Is there visible evidence in the image that supports this procedure?
2. Does the tooth/location match what's shown in the image?
3. Is the severity/condition shown in the image consistent with the procedure?

Also check for:
- Findings visible in the image that are NOT being billed (missed revenue)
- Obvious discrepancies between the image and the codes
- Documentation gaps that could lead to denial

Return your response as JSON:
{
  "verifications": [
    {
      "cdt_code": "D2740",
      "status": "supported" | "unsupported" | "inconclusive",
      "confidence": 85,
      "finding": "What you see in the image for this procedure",
      "concern": "Any concern or issue (null if none)",
      "recommendation": "What to do about it (null if fine)"
    }
  ],
  "missed_findings": [
    {
      "description": "Finding visible in image not covered by any coded procedure",
      "tooth_number": "14",
      "suggested_code": "D3310",
      "suggested_description": "Root canal - anterior",
      "reasoning": "Why this finding suggests additional treatment"
    }
  ],
  "overall_assessment": {
    "documentation_strength": "strong" | "moderate" | "weak",
    "denial_risk": "low" | "medium" | "high",
    "summary": "Brief overall assessment"
  }
}

Rules:
- Be thorough but honest — only flag real concerns.
- "supported" means the image clearly shows evidence for the procedure.
- "unsupported" means the image contradicts the procedure or shows no evidence.
- "inconclusive" means you can't determine from this image alone.
- For missed findings, only flag things that are clearly visible.
- Return ONLY valid JSON. No additional text.
"""


class ImageProcedureVerifier:
    """Verifies dental images against coded procedures using Claude Vision."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def verify(
        self,
        image_data: bytes,
        media_type: str,
        coded_procedures: list[dict],
        clinical_notes: str | None = None,
    ) -> VerificationResult:
        """
        Verify that an image supports the coded procedures.

        Args:
            image_data: Raw image bytes
            media_type: MIME type (image/png, image/jpeg, etc.)
            coded_procedures: List of dicts with cdt_code, cdt_description,
                            tooth_number, surfaces
            clinical_notes: Optional clinical notes for context

        Returns:
            VerificationResult with per-procedure status and missed findings
        """
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        procedures_text = "\n".join(
            f"- {p['cdt_code']}: {p['cdt_description']}"
            + (f" (tooth {p['tooth_number']})" if p.get("tooth_number") else "")
            + (f" (surfaces: {p['surfaces']})" if p.get("surfaces") else "")
            for p in coded_procedures
        )

        user_text = f"Coded procedures to verify:\n{procedures_text}"
        if clinical_notes:
            user_text += f"\n\nClinical notes for context:\n{clinical_notes}"

        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
            {"type": "text", "text": user_text},
        ]

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=VERIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)

        return VerificationResult(
            verifications=[
                ProcedureVerification(**v) for v in data.get("verifications", [])
            ],
            missed_findings=[
                MissedFinding(**f) for f in data.get("missed_findings", [])
            ],
            overall_assessment=data.get("overall_assessment", {}),
        )

    async def verify_multiple_images(
        self,
        images: list[tuple[bytes, str]],
        coded_procedures: list[dict],
        clinical_notes: str | None = None,
    ) -> VerificationResult:
        """Verify against multiple images (e.g., BWX set + periapical)."""
        # Use the first image for now; could be extended to multi-image analysis
        if not images:
            return VerificationResult(
                verifications=[],
                missed_findings=[],
                overall_assessment={
                    "documentation_strength": "weak",
                    "denial_risk": "high",
                    "summary": "No images provided for verification.",
                },
            )
        image_data, media_type = images[0]
        return await self.verify(image_data, media_type, coded_procedures, clinical_notes)


class ProcedureVerification:
    """Verification result for a single coded procedure."""

    def __init__(
        self,
        cdt_code: str,
        status: str,
        confidence: int,
        finding: str,
        concern: str | None = None,
        recommendation: str | None = None,
    ):
        self.cdt_code = cdt_code
        self.status = status  # supported, unsupported, inconclusive
        self.confidence = confidence
        self.finding = finding
        self.concern = concern
        self.recommendation = recommendation

    def to_dict(self) -> dict:
        return {
            "cdt_code": self.cdt_code,
            "status": self.status,
            "confidence": self.confidence,
            "finding": self.finding,
            "concern": self.concern,
            "recommendation": self.recommendation,
        }


class MissedFinding:
    """A finding visible in the image not covered by any coded procedure."""

    def __init__(
        self,
        description: str,
        tooth_number: str | None = None,
        suggested_code: str | None = None,
        suggested_description: str | None = None,
        reasoning: str | None = None,
    ):
        self.description = description
        self.tooth_number = tooth_number
        self.suggested_code = suggested_code
        self.suggested_description = suggested_description
        self.reasoning = reasoning

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "tooth_number": self.tooth_number,
            "suggested_code": self.suggested_code,
            "suggested_description": self.suggested_description,
            "reasoning": self.reasoning,
        }


class VerificationResult:
    """Complete verification result."""

    def __init__(
        self,
        verifications: list[ProcedureVerification],
        missed_findings: list[MissedFinding],
        overall_assessment: dict,
    ):
        self.verifications = verifications
        self.missed_findings = missed_findings
        self.overall_assessment = overall_assessment

    @property
    def has_issues(self) -> bool:
        return any(
            v.status != "supported" for v in self.verifications
        ) or len(self.missed_findings) > 0

    @property
    def unsupported_codes(self) -> list[str]:
        return [v.cdt_code for v in self.verifications if v.status == "unsupported"]

    def to_dict(self) -> dict:
        return {
            "verifications": [v.to_dict() for v in self.verifications],
            "missed_findings": [f.to_dict() for f in self.missed_findings],
            "overall_assessment": self.overall_assessment,
        }
