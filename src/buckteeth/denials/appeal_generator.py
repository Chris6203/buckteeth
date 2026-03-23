"""Claude-powered appeal letter generator for denied dental insurance claims.

Generates formal, payer-specific appeal letters citing relevant case law,
regulatory references, and payer-specific appeal requirements.
"""

from __future__ import annotations

import json
import re

import anthropic

from buckteeth.knowledge.case_law import CaseLawRepository
from buckteeth.denials.schemas import AppealRequest, AppealResponse
from buckteeth.edi.payer_directory import payer_directory

# Payer-specific appeal requirements and strategies
PAYER_APPEAL_INFO: dict[str, dict] = {
    "Delta Dental": {
        "appeal_address": "Delta Dental Appeals Department, P.O. Box 997330, Sacramento, CA 95899",
        "appeal_deadline_days": 180,
        "appeal_format": "Written letter with supporting documentation",
        "known_strategies": [
            "Delta Dental responds well to ADA guidelines citations",
            "Include full periodontal charting for SRP appeals",
            "Reference the specific Delta Dental plan benefit booklet language",
        ],
        "required_attachments": ["Copy of EOB", "Clinical notes", "Radiographs"],
    },
    "MetLife": {
        "appeal_address": "MetLife Dental Claims Review, P.O. Box 981282, El Paso, TX 79998",
        "appeal_deadline_days": 180,
        "appeal_format": "Written appeal with ADA claim form attached",
        "known_strategies": [
            "MetLife often overturns crown denials when pre-op radiograph clearly shows pathology",
            "Include percentage of tooth structure compromised for crown appeals",
            "Reference MetLife's own provider manual criteria",
        ],
        "required_attachments": ["Pre-op radiograph", "ADA claim form copy", "Narrative"],
    },
    "Cigna": {
        "appeal_address": "Cigna Dental Appeals, P.O. Box 188044, Chattanooga, TN 37422",
        "appeal_deadline_days": 90,
        "appeal_format": "Written appeal referencing claim number",
        "known_strategies": [
            "Cigna requires full periodontal charting with pocket depths for SRP appeals",
            "Include AAP periodontal classification in the appeal",
            "Reference Cigna's clinical criteria document",
        ],
        "required_attachments": ["Periodontal charting", "Radiographs", "Clinical narrative"],
    },
    "Aetna": {
        "appeal_address": "Aetna Dental Appeals, P.O. Box 14094, Lexington, KY 40512",
        "appeal_deadline_days": 180,
        "appeal_format": "Written appeal with clinical documentation",
        "known_strategies": [
            "Aetna responds to evidence-based treatment justification",
            "Include ADA/AAP guidelines that support the treatment",
            "Reference Aetna's Clinical Policy Bulletin for dental procedures",
        ],
        "required_attachments": ["Clinical notes", "Radiographs", "Copy of original claim"],
    },
    "Guardian": {
        "appeal_address": "Guardian Dental Appeals, P.O. Box 659608, San Antonio, TX 78265",
        "appeal_deadline_days": 120,
        "appeal_format": "Written letter with supporting documentation",
        "known_strategies": [
            "Guardian accepts detailed clinical narratives with measurements",
            "Include pre-operative photographs when available",
        ],
        "required_attachments": ["Clinical narrative", "Radiographs"],
    },
    "UnitedHealthcare": {
        "appeal_address": "UHC Dental Appeals, P.O. Box 30567, Salt Lake City, UT 84130",
        "appeal_deadline_days": 180,
        "appeal_format": "Written appeal with all supporting documentation",
        "known_strategies": [
            "UHC responds well to comparative treatment cost analysis",
            "Include documentation showing treatment alternatives were considered",
        ],
        "required_attachments": ["Clinical records", "Radiographs", "Treatment plan"],
    },
}

APPEAL_SYSTEM_PROMPT = """\
You are a dental insurance appeals specialist and healthcare attorney. Your job is to write \
formal, payer-specific appeal letters for denied dental insurance claims.

CRITICAL REQUIREMENTS:
- Address the letter to the specific insurance company's appeal department.
- Reference the patient's specific plan, subscriber ID, and claim details.
- Cite the specific denial reason code and explain why it is incorrect.
- Include relevant case law, regulatory citations, and ADA/AAP guidelines.
- Use clinical evidence from the provider's notes to build the argument.
- Reference state insurance regulations that protect the patient's right to coverage.
- If payer-specific strategies are provided, incorporate them.
- Include a clear "requested action" — what you want the payer to do.
- Be professional, firm, and detailed — this is a legal document.

FORMAT the letter as a proper business letter with:
- Date
- Insurance company name and address
- Re: line with patient name, subscriber ID, claim details
- Salutation
- Body paragraphs (introduction, clinical justification, legal arguments, requested action)
- Closing with provider signature block

Return your response as JSON:
{
  "appeal_text": "<complete formatted appeal letter>",
  "case_law_citations": ["<list of case law citations used>"],
  "key_arguments": ["<list of key arguments made>"],
  "recommended_attachments": ["<list of documents to include with the appeal>"]
}
Return ONLY the JSON object, no additional text.
"""


class AppealGenerator:
    """Generates formal, payer-specific appeal letters using Claude."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._case_law_repo = CaseLawRepository()

    async def generate_appeal(self, request: AppealRequest) -> AppealResponse:
        """Generate a formal appeal letter tailored to the specific payer."""
        # 1. Get relevant case law
        citations = self._case_law_repo.get_relevant_citations(
            denial_code=request.denial_reason_code,
            procedure_code=request.cdt_code,
            state=request.state,
        )

        # 2. Get payer-specific info
        payer_info = self._get_payer_info(request.payer_name)

        # 3. Get payer rules from directory
        payer_rules = self._get_payer_rules(request.payer_name, request.cdt_code)

        # 4. Build the prompt
        user_prompt = self._build_prompt(request, citations, payer_info, payer_rules)

        # 5. Call Claude
        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=APPEAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # 6. Parse response
        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)

        # Add payer-specific required attachments
        recommended = data.get("recommended_attachments", [])
        if payer_info and payer_info.get("required_attachments"):
            for att in payer_info["required_attachments"]:
                if att not in recommended:
                    recommended.append(att)

        return AppealResponse(
            appeal_text=data["appeal_text"],
            case_law_citations=data["case_law_citations"],
            key_arguments=data["key_arguments"],
            recommended_attachments=recommended,
        )

    def _get_payer_info(self, payer_name: str) -> dict | None:
        """Get payer-specific appeal information."""
        # Try exact match first
        for key, info in PAYER_APPEAL_INFO.items():
            if key.lower() in payer_name.lower():
                return info
        return None

    def _get_payer_rules(self, payer_name: str, cdt_code: str) -> dict:
        """Get payer rules from our directory for context."""
        results = payer_directory.search(payer_name)
        if not results:
            return {}

        payer = results[0]
        freq_rule = payer.frequency_rules.get(cdt_code, "")
        needs_preauth = cdt_code in payer.preauth_required_codes

        return {
            "payer_id": payer.payer_id,
            "frequency_rule": freq_rule,
            "preauth_required": needs_preauth,
            "common_denial_codes": payer.common_denial_codes[:5],
        }

    @staticmethod
    def _build_prompt(
        request: AppealRequest,
        citations,
        payer_info: dict | None,
        payer_rules: dict,
    ) -> str:
        """Build the prompt with all available context."""
        case_law_text = ""
        for c in citations[:5]:
            case_law_text += f"\n- {c.citation}: {c.key_principle}"

        payer_context = ""
        if payer_info:
            payer_context = f"""
Payer-Specific Appeal Information:
- Appeal Address: {payer_info.get('appeal_address', 'Unknown')}
- Appeal Deadline: {payer_info.get('appeal_deadline_days', 180)} days from denial
- Required Format: {payer_info.get('appeal_format', 'Written letter')}
- Required Attachments: {', '.join(payer_info.get('required_attachments', []))}
- Strategies Known to Work with This Payer:
{chr(10).join(f'  * {s}' for s in payer_info.get('known_strategies', []))}
"""

        rules_context = ""
        if payer_rules:
            rules_context = f"""
Payer Rules for This Procedure:
- Payer ID: {payer_rules.get('payer_id', 'Unknown')}
- Frequency Limitation: {payer_rules.get('frequency_rule', 'None found')}
- Pre-authorization Required: {'Yes' if payer_rules.get('preauth_required') else 'No'}
"""

        from datetime import date as _date
        today = _date.today().strftime("%B %d, %Y")

        # Load practice settings for provider info
        import json as _json
        practice_name = ""
        practice_address = ""
        practice_phone = ""
        try:
            import os as _os
            settings_file = _os.environ.get("SETTINGS_FILE", "/opt/buckteeth/practice_settings.json")
            with open(settings_file) as f:
                ps = _json.load(f)
                practice_name = ps.get("practice_name", "")
                addr_parts = [ps.get("address_line1", ""), ps.get("city", ""), ps.get("state", ""), ps.get("zip", "")]
                practice_address = ", ".join(p for p in addr_parts if p)
                practice_phone = ps.get("phone", "")
        except Exception:
            pass

        return f"""TODAY'S DATE: {today} (use this as the letter date)

IMPORTANT: Do NOT use placeholder brackets like [Insert X]. Use the actual values provided below.
If a value is not available, omit it rather than using a placeholder.

Practice Information:
- Practice Name: {practice_name or request.provider_name}
- Practice Address: {practice_address or 'On file'}
- Practice Phone: {practice_phone or 'On file'}

Denial Details:
- Patient: {request.patient_name}
- Provider: {request.provider_name}
- Date of Service: {request.date_of_service}
- CDT Code: {request.cdt_code} - {request.procedure_description}
- Denial Reason Code: {request.denial_reason_code}
- Denial Reason: {request.denial_reason_description}
- Denied Amount: ${request.denied_amount:.2f}
- Payer: {request.payer_name}
- State: {request.state}

Clinical Notes from Provider:
{request.clinical_notes}
{payer_context}{rules_context}
Relevant Case Law and Regulations:
{case_law_text if case_law_text else "No specific case law found — use general dental insurance regulations and ADA guidelines."}

Generate a formal appeal letter addressed to this specific insurance company, citing the clinical evidence and legal arguments above. The letter should be ready to print and mail."""
