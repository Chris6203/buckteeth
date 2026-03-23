import json
import re
from dataclasses import dataclass
from datetime import datetime

import anthropic

from buckteeth.knowledge.payer_rules import PayerRuleRepository


@dataclass
class RiskAssessment:
    risk_score: int  # 0-100
    risk_level: str  # low, medium, high
    risk_factors: list[str]
    recommendations: list[str]


RISK_SYSTEM_PROMPT = """\
You are a dental insurance claims risk analyst. Your job is to predict the \
likelihood of claim denial BEFORE submission.

Analyze the claim details and assess denial risk based on:
1. Procedure type and payer patterns (certain payers frequently deny specific codes)
2. Frequency limitations (e.g., crowns every 5 years, BWX 1x/year, prophy 2x/year)
3. Missing documentation (narratives, x-rays, pre-authorization)
4. Code bundling issues
5. Patient age appropriateness for procedures
6. Known payer-specific denial patterns

Return as JSON:
{
  "risk_score": <0-100>,
  "risk_level": "<low|medium|high>",
  "risk_factors": ["<list of specific risk factors>"],
  "recommendations": ["<list of actions to reduce denial risk>"]
}

Risk levels: low (0-30), medium (31-60), high (61-100)
Return ONLY the JSON object.
"""


# Common frequency limits in months
FREQUENCY_LIMITS = {
    "D0120": 6,     # Periodic oral eval - 2x/year
    "D0150": 36,    # Comprehensive oral eval - every 3 years
    "D0210": 60,    # FMX - every 5 years
    "D0274": 12,    # BWX - 1x/year
    "D1110": 6,     # Prophy - 2x/year
    "D1120": 6,     # Child prophy - 2x/year
    "D2740": 60,    # Crown porcelain - every 5 years
    "D2750": 60,    # Crown porcelain-metal - every 5 years
    "D4341": 24,    # SRP - every 2 years
    "D4342": 24,    # SRP 1-3 teeth - every 2 years
}


class DenialRiskScorer:
    """Predicts denial probability using rule-based checks + Claude analysis."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._payer_rules = PayerRuleRepository()

    async def assess(
        self,
        cdt_codes: list[str],
        payer_name: str,
        payer_id: str,
        patient_age: int,
        provider_name: str,
        date_of_service: str,
        clinical_notes: str,
        last_service_dates: dict[str, str] | None = None,
    ) -> RiskAssessment:
        # 1. Rule-based pre-checks
        rule_factors = self._check_frequency_risks(
            cdt_codes, payer_name, last_service_dates or {}
        )

        # 2. Claude-based risk analysis
        user_prompt = self._build_prompt(
            cdt_codes, payer_name, patient_age, provider_name,
            date_of_service, clinical_notes, rule_factors,
        )

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=RISK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)

        return RiskAssessment(
            risk_score=data["risk_score"],
            risk_level=data["risk_level"],
            risk_factors=data["risk_factors"],
            recommendations=data["recommendations"],
        )

    def _check_frequency_risks(
        self,
        cdt_codes: list[str],
        payer_name: str,
        last_service_dates: dict[str, str],
    ) -> list[str]:
        factors = []
        today = datetime.now().date()

        for code in cdt_codes:
            limit_months = FREQUENCY_LIMITS.get(code)
            if limit_months is None:
                continue

            last_date_str = last_service_dates.get(code)
            if last_date_str is None:
                continue

            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            months_since = (today - last_date).days / 30.44

            if months_since < limit_months:
                factors.append(
                    f"Frequency limit: {code} last performed {last_date_str} "
                    f"({months_since:.0f} months ago), "
                    f"typical limit is {limit_months} months"
                )

        return factors

    @staticmethod
    def _build_prompt(cdt_codes, payer_name, patient_age, provider_name,
                      date_of_service, clinical_notes, rule_factors) -> str:
        rule_section = ""
        if rule_factors:
            rule_section = "\n\nPre-identified risk factors:\n" + "\n".join(
                f"- {f}" for f in rule_factors
            )

        return f"""Claim Details:
- CDT Codes: {', '.join(cdt_codes)}
- Payer: {payer_name}
- Patient Age: {patient_age}
- Provider: {provider_name}
- Date of Service: {date_of_service}

Clinical Notes:
{clinical_notes}
{rule_section}

Assess the denial risk for this claim."""
