"""Denial feedback learning system.

Ingests claim denials, extracts patterns, and updates payer-specific rules
so future claims avoid the same issues.  Operates entirely in-memory (no
database dependency) and can be backed by persistent storage later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from buckteeth.edi.x12_835 import (
    CARC_CODES,
    RemittanceAdvice,
)


# ---------------------------------------------------------------------------
# CARC -> actionable rule mapping (top 30+ codes)
# ---------------------------------------------------------------------------
_CARC_RULES: dict[str, str] = {
    "1": (
        "Deductible not met -- verify remaining deductible before scheduling "
        "major services and inform the patient of their out-of-pocket cost."
    ),
    "2": (
        "Coinsurance amount -- ensure the patient portion is collected at "
        "time of service to avoid balance-collection issues."
    ),
    "3": (
        "Copayment amount -- collect the correct copay at check-in per "
        "the patient's plan schedule."
    ),
    "4": (
        "Service not covered by this payer -- verify coverage and benefits "
        "eligibility (270/271) before performing the procedure."
    ),
    "16": (
        "Claim lacks required information -- review submission for missing "
        "fields (tooth number, surface, date of service, diagnosis)."
    ),
    "18": (
        "Duplicate claim/service -- check claim history before resubmitting; "
        "if this is a corrected claim, use the appropriate frequency code."
    ),
    "22": (
        "Care may be covered by another payer -- confirm coordination of "
        "benefits (COB) and submit to the primary payer first."
    ),
    "23": (
        "Charges exceed the payer fee schedule -- adjust fees to match "
        "contracted rates or appeal with supporting documentation."
    ),
    "24": (
        "Charges covered under capitation agreement -- do not bill "
        "fee-for-service for capitated procedures."
    ),
    "29": (
        "Time limit for filing has expired -- submit claims within the "
        "payer's filing deadline (typically 90-365 days from DOS)."
    ),
    "31": (
        "Service not covered by the patient's current benefit plan -- "
        "verify active coverage and plan limitations before treatment."
    ),
    "45": (
        "Charges exceed the maximum allowable amount -- bill at or below "
        "the contracted fee schedule for this payer."
    ),
    "50": (
        "Non-covered service -- check the patient's plan for exclusions; "
        "consider an alternative covered procedure code or patient self-pay."
    ),
    "96": (
        "Non-covered charge -- the service is excluded from the plan; "
        "inform the patient in advance and collect full fee if proceeding."
    ),
    "97": (
        "Payment already made for this service -- verify claim history "
        "to avoid duplicate billing."
    ),
    "119": (
        "Annual/lifetime benefit maximum has been reached -- check "
        "remaining benefits before scheduling and advise the patient."
    ),
    "128": (
        "Newborn services are covered under the mother's claim -- "
        "bill under the mother's subscriber ID."
    ),
    "146": (
        "Diagnosis is inconsistent with the procedure -- ensure the "
        "ICD/diagnosis code supports medical necessity for the CDT code."
    ),
    "167": (
        "A more specific diagnosis code is required -- update the "
        "diagnosis to the most specific ICD code available."
    ),
    "170": (
        "Claim contains a date of service in the future -- correct "
        "the date of service to the actual treatment date."
    ),
    "197": (
        "Precertification, authorization, or notification was not obtained -- "
        "always obtain preauthorization for procedures that require it."
    ),
    "204": (
        "Service is not covered unless specific conditions are met -- "
        "include supporting documentation or narrative to justify necessity."
    ),
    "242": (
        "Service not provided by an in-network provider -- verify network "
        "participation or obtain an out-of-network referral/authorization."
    ),
    "253": (
        "Sequestration reduction applied -- this is a mandatory federal "
        "reduction; no corrective action, but account for it in estimates."
    ),
    "N362": (
        "Missing or invalid tooth number -- include the correct tooth "
        "number (1-32 universal, or A-T primary) on the claim."
    ),
    "N382": (
        "Missing or invalid tooth surface -- specify the correct surface "
        "designation (M, O, D, B/F, L/I) on restorative claims."
    ),
    "N432": (
        "Eligibility response (271) was not received -- verify eligibility "
        "through an alternative channel before submitting the claim."
    ),
    # Additional common CARC codes beyond the x12_835 module set
    "5": (
        "Procedure code is inconsistent with the modifier or missing a "
        "required modifier -- review and attach the correct modifier."
    ),
    "6": (
        "Procedure/revenue code is inconsistent with the patient's age -- "
        "verify age-limited procedures (sealants, fluoride) against DOB."
    ),
    "9": (
        "Diagnosis is inconsistent with the patient's age -- confirm the "
        "diagnosis code is appropriate for the patient's age group."
    ),
    "11": (
        "Diagnosis is inconsistent with the place of service -- ensure "
        "POS code matches where the service was actually rendered."
    ),
    "27": (
        "Expenses incurred after coverage was terminated -- verify the "
        "patient's coverage end date before providing services."
    ),
    "35": (
        "Lifetime benefit maximum has been reached for this service -- "
        "inform the patient that no further plan benefits are available."
    ),
    "39": (
        "Services denied at the time authorization/pre-cert was requested -- "
        "do not proceed without an approved authorization on file."
    ),
    "49": (
        "Routine/preventive care is not covered under this plan -- "
        "verify whether preventive benefits exist or bill patient directly."
    ),
    "55": (
        "Procedure/treatment/drug is deemed experimental or investigational -- "
        "use a standard, accepted procedure code instead."
    ),
    "58": (
        "Service was provided as part of a package/bundled procedure -- "
        "do not bill component codes separately."
    ),
    "59": (
        "Services are processed under a different plan/benefit -- route "
        "the claim to the correct plan or payer."
    ),
    "89": (
        "Services not provided or authorized by the designated gatekeeper -- "
        "obtain a referral from the patient's primary care provider."
    ),
    "109": (
        "Claim not covered by this payer -- verify payer assignment and "
        "coordination of benefits order."
    ),
    "129": (
        "Prior processing information appears incorrect -- review and "
        "correct any previously adjudicated claim data."
    ),
    "136": (
        "Failure to follow plan network composition/guidelines -- ensure "
        "services comply with the managed care network rules."
    ),
    "151": (
        "Payment adjusted because the payer deems the information "
        "submitted does not support this level of service."
    ),
    "181": (
        "Procedure code was replaced by a more appropriate code -- use "
        "the payer-preferred CDT code for this service."
    ),
    "198": (
        "Precertification was not obtained in a timely fashion -- submit "
        "preauthorization requests within the required timeframe."
    ),
    "219": (
        "Claim denied based on plan benefit waiting period -- verify "
        "the patient has satisfied any waiting period for this benefit class."
    ),
    "226": (
        "Information requested was not provided or was insufficient -- "
        "respond to payer requests for documentation promptly."
    ),
    "234": (
        "This service has been bundled with another service performed "
        "on the same date -- review bundling/unbundling rules."
    ),
    "235": (
        "Sales tax -- this amount represents sales tax and is the "
        "patient's responsibility."
    ),
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class DenialPattern:
    """A recurring denial pattern for a specific payer and procedure."""

    payer_id: str
    cdt_code: str
    denial_reason_code: str
    denial_reason_description: str
    frequency: int
    first_seen: str  # ISO date
    last_seen: str  # ISO date
    learned_rule: str | None = None
    resolved: bool = False


# ---------------------------------------------------------------------------
# Denial Feedback Engine
# ---------------------------------------------------------------------------
class DenialFeedbackEngine:
    """Ingests claim denials, extracts patterns, and derives payer-specific rules.

    All data is stored in memory.  The engine is designed to be fed denial
    information from the API layer (either individual denials or full 835 ERAs).
    """

    def __init__(self) -> None:
        self._patterns: dict[str, list[DenialPattern]] = {}

    # -- ingestion ----------------------------------------------------------

    def ingest_denial(
        self,
        payer_id: str,
        cdt_code: str,
        reason_code: str,
        reason_description: str,
        denied_amount: float,
        date: str,
    ) -> DenialPattern:
        """Record a single denial and return the (updated or new) pattern.

        If a pattern already exists for this *payer_id* + *cdt_code* +
        *reason_code* combination, the frequency is incremented and
        ``last_seen`` is updated.  Otherwise a new pattern is created and
        a rule is derived if possible.
        """
        existing = self._find_pattern(payer_id, cdt_code, reason_code)
        if existing is not None:
            existing.frequency += 1
            if date > existing.last_seen:
                existing.last_seen = date
            if date < existing.first_seen:
                existing.first_seen = date
            # Re-derive the rule if one was never set
            if existing.learned_rule is None:
                existing.learned_rule = self.derive_rule(
                    reason_code, reason_description, cdt_code,
                )
            return existing

        rule = self.derive_rule(reason_code, reason_description, cdt_code)
        pattern = DenialPattern(
            payer_id=payer_id,
            cdt_code=cdt_code,
            denial_reason_code=reason_code,
            denial_reason_description=reason_description,
            frequency=1,
            first_seen=date,
            last_seen=date,
            learned_rule=rule,
        )
        self._patterns.setdefault(payer_id, []).append(pattern)
        return pattern

    def ingest_era(self, remittance: RemittanceAdvice) -> list[DenialPattern]:
        """Process all denied service lines in an ERA and return patterns."""
        results: list[DenialPattern] = []
        payer_id = remittance.payer_id

        for claim in remittance.claims:
            # Consider both fully denied claims and individual service denials
            is_denied_claim = claim.claim_status == "denied"

            for svc in claim.service_payments:
                denial_adjustments = [
                    adj for adj in svc.adjustments
                    if adj.group_code in ("CO", "PI", "OA")
                    and adj.amount > 0
                    and adj.reason_code not in ("1", "2", "3")  # skip deductible/coins/copay
                ]

                if is_denied_claim and not denial_adjustments:
                    # Claim-level denial with no service adjustments --
                    # record a generic denial for each service line.
                    pattern = self.ingest_denial(
                        payer_id=payer_id,
                        cdt_code=svc.cdt_code,
                        reason_code="4",
                        reason_description=CARC_CODES.get("4", "Service not covered"),
                        denied_amount=svc.charge_amount - svc.paid_amount,
                        date=claim.check_date or date.today().isoformat(),
                    )
                    results.append(pattern)
                else:
                    for adj in denial_adjustments:
                        description = (
                            CARC_CODES.get(adj.reason_code)
                            or adj.reason_description
                        )
                        pattern = self.ingest_denial(
                            payer_id=payer_id,
                            cdt_code=svc.cdt_code,
                            reason_code=adj.reason_code,
                            reason_description=description,
                            denied_amount=adj.amount,
                            date=claim.check_date or date.today().isoformat(),
                        )
                        results.append(pattern)

        return results

    # -- queries ------------------------------------------------------------

    def get_patterns(self, payer_id: str) -> list[DenialPattern]:
        """Return all denial patterns for a payer."""
        return list(self._patterns.get(payer_id, []))

    def get_top_denial_reasons(
        self, payer_id: str, limit: int = 10
    ) -> list[DenialPattern]:
        """Return the most frequent denial patterns for a payer."""
        patterns = self._patterns.get(payer_id, [])
        return sorted(patterns, key=lambda p: p.frequency, reverse=True)[:limit]

    def get_risk_for_procedure(
        self, payer_id: str, cdt_code: str
    ) -> dict:
        """Assess denial risk for a specific procedure with a specific payer.

        Returns a dict with ``risk_level``, ``denial_count``,
        ``common_reasons``, and ``recommendations``.
        """
        patterns = [
            p for p in self._patterns.get(payer_id, [])
            if p.cdt_code == cdt_code
        ]

        total_denials = sum(p.frequency for p in patterns)

        if total_denials == 0:
            return {
                "risk_level": "low",
                "denial_count": 0,
                "common_reasons": [],
                "recommendations": [],
            }

        # Determine risk level based on denial frequency
        if total_denials >= 10:
            risk_level = "high"
        elif total_denials >= 3:
            risk_level = "medium"
        else:
            risk_level = "low"

        common_reasons = [
            {
                "reason_code": p.denial_reason_code,
                "description": p.denial_reason_description,
                "count": p.frequency,
            }
            for p in sorted(patterns, key=lambda p: p.frequency, reverse=True)
        ]

        recommendations = []
        for p in patterns:
            if p.learned_rule and p.learned_rule not in recommendations:
                recommendations.append(p.learned_rule)

        return {
            "risk_level": risk_level,
            "denial_count": total_denials,
            "common_reasons": common_reasons,
            "recommendations": recommendations,
        }

    def check_claim_against_patterns(
        self, payer_id: str, procedures: list[dict]
    ) -> list[dict]:
        """Check a list of procedures against known denial patterns.

        Each item in *procedures* should be a dict with at least a
        ``cdt_code`` key.  Returns a list of warning dicts for procedures
        that have known denial patterns with this payer.
        """
        warnings: list[dict] = []
        payer_patterns = self._patterns.get(payer_id, [])
        if not payer_patterns:
            return warnings

        for proc in procedures:
            cdt_code = proc.get("cdt_code", "")
            matching = [p for p in payer_patterns if p.cdt_code == cdt_code]

            for pattern in matching:
                warning: dict = {
                    "cdt_code": cdt_code,
                    "reason_code": pattern.denial_reason_code,
                    "reason_description": pattern.denial_reason_description,
                    "denial_count": pattern.frequency,
                    "last_seen": pattern.last_seen,
                    "recommendation": pattern.learned_rule or (
                        f"This procedure has been denied {pattern.frequency} "
                        f"time(s) by this payer for: {pattern.denial_reason_description}"
                    ),
                }
                warnings.append(warning)

        return warnings

    # -- rule derivation ----------------------------------------------------

    @staticmethod
    def derive_rule(
        reason_code: str, reason_description: str, cdt_code: str
    ) -> str | None:
        """Derive a human-readable, actionable rule from a denial reason code.

        Uses the comprehensive ``_CARC_RULES`` mapping and falls back to
        heuristic analysis of the description text when the code is not
        in the mapping.
        """
        # Direct lookup in the comprehensive mapping
        rule = _CARC_RULES.get(reason_code)
        if rule:
            return rule

        # Heuristic fallback: try to infer from the description text
        if not reason_description:
            return None

        desc_lower = reason_description.lower()

        if "maximum" in desc_lower or "limit" in desc_lower:
            return (
                "Benefit maximum or frequency limit reached -- verify "
                "remaining benefits before scheduling this procedure."
            )
        if "timely" in desc_lower or "time limit" in desc_lower or "filing" in desc_lower:
            return (
                "Filing deadline issue -- ensure claims are submitted "
                "within the payer's timely filing window."
            )
        if "duplicate" in desc_lower:
            return (
                "Possible duplicate claim -- check claim history before "
                "resubmitting."
            )
        if "authorization" in desc_lower or "precert" in desc_lower:
            return (
                "Prior authorization was required -- obtain preauthorization "
                "before performing this procedure for this payer."
            )
        if "not covered" in desc_lower or "non-covered" in desc_lower:
            return (
                "Service is not a covered benefit -- verify plan coverage "
                "or use an alternative procedure code."
            )
        if "eligib" in desc_lower:
            return (
                "Patient eligibility issue -- verify active coverage "
                "before rendering services."
            )
        if "tooth" in desc_lower and ("missing" in desc_lower or "invalid" in desc_lower):
            return (
                "Tooth number is missing or invalid -- include the correct "
                "tooth number on the claim form."
            )
        if "surface" in desc_lower and ("missing" in desc_lower or "invalid" in desc_lower):
            return (
                "Tooth surface is missing or invalid -- include the correct "
                "surface designation on restorative claims."
            )
        if "bundl" in desc_lower or "component" in desc_lower or "incidental" in desc_lower:
            return (
                "Procedure is bundled with another service -- do not bill "
                "component codes separately."
            )
        if "network" in desc_lower:
            return (
                "Service must be provided by an in-network provider -- "
                "verify network participation status."
            )
        if "diagnosis" in desc_lower or "dx" in desc_lower:
            return (
                "Diagnosis issue -- ensure the submitted diagnosis code "
                "supports the procedure and matches payer requirements."
            )
        if "age" in desc_lower:
            return (
                "Age restriction on this procedure -- verify the patient "
                "meets the age criteria for this benefit."
            )
        if "waiting period" in desc_lower:
            return (
                "Plan waiting period has not been satisfied -- confirm "
                "the patient is past the waiting period for this class."
            )

        return None

    # -- internal helpers ---------------------------------------------------

    def _find_pattern(
        self, payer_id: str, cdt_code: str, reason_code: str
    ) -> DenialPattern | None:
        """Find an existing pattern by payer + code + reason."""
        for pattern in self._patterns.get(payer_id, []):
            if (
                pattern.cdt_code == cdt_code
                and pattern.denial_reason_code == reason_code
            ):
                return pattern
        return None


# ---------------------------------------------------------------------------
# Practice Insights
# ---------------------------------------------------------------------------
class PracticeInsights:
    """High-level reporting and recommendations built on top of the
    :class:`DenialFeedbackEngine`.
    """

    def __init__(self, engine: DenialFeedbackEngine) -> None:
        self._engine = engine

    def generate_payer_report(self, payer_id: str) -> dict:
        """Generate a denial analytics report for a single payer.

        Returns a dict with ``payer_id``, ``total_denials``,
        ``unique_patterns``, ``top_denial_reasons``,
        ``most_problematic_codes``, and ``denial_rate_trend``.
        """
        patterns = self._engine.get_patterns(payer_id)
        total_denials = sum(p.frequency for p in patterns)

        # Top denial reasons (by frequency)
        top_reasons = self._engine.get_top_denial_reasons(payer_id, limit=10)

        # Most problematic CDT codes (aggregate across reason codes)
        code_totals: dict[str, int] = {}
        for p in patterns:
            code_totals[p.cdt_code] = code_totals.get(p.cdt_code, 0) + p.frequency
        most_problematic = sorted(
            code_totals.items(), key=lambda kv: kv[1], reverse=True
        )[:10]

        # Simple trend indicator based on recency
        trend = self._compute_trend(patterns)

        return {
            "payer_id": payer_id,
            "total_denials": total_denials,
            "unique_patterns": len(patterns),
            "top_denial_reasons": [
                {
                    "reason_code": p.denial_reason_code,
                    "description": p.denial_reason_description,
                    "count": p.frequency,
                    "learned_rule": p.learned_rule,
                }
                for p in top_reasons
            ],
            "most_problematic_codes": [
                {"cdt_code": code, "denial_count": count}
                for code, count in most_problematic
            ],
            "denial_rate_trend": trend,
        }

    def generate_practice_report(self) -> dict:
        """Generate a denial analytics report across all payers.

        Returns a dict with ``total_denials``, ``total_patterns``,
        ``worst_payers``, ``most_denied_procedures``, and
        ``estimated_revenue_lost``.
        """
        all_patterns: list[DenialPattern] = []
        payer_totals: dict[str, int] = {}
        code_totals: dict[str, int] = {}

        for payer_id, patterns in self._engine._patterns.items():
            payer_sum = 0
            for p in patterns:
                all_patterns.append(p)
                payer_sum += p.frequency
                code_totals[p.cdt_code] = (
                    code_totals.get(p.cdt_code, 0) + p.frequency
                )
            payer_totals[payer_id] = payer_sum

        total_denials = sum(payer_totals.values())

        worst_payers = sorted(
            payer_totals.items(), key=lambda kv: kv[1], reverse=True
        )[:10]

        most_denied = sorted(
            code_totals.items(), key=lambda kv: kv[1], reverse=True
        )[:10]

        # Rough revenue-lost estimate is not possible without dollar amounts
        # stored in patterns; provide the denial count as a proxy.
        return {
            "total_denials": total_denials,
            "total_patterns": len(all_patterns),
            "worst_payers": [
                {"payer_id": pid, "denial_count": count}
                for pid, count in worst_payers
            ],
            "most_denied_procedures": [
                {"cdt_code": code, "denial_count": count}
                for code, count in most_denied
            ],
            "estimated_revenue_lost": (
                "Revenue impact data requires denied-amount tracking. "
                f"Total denial events recorded: {total_denials}."
            ),
        }

    def get_recommendations(self, payer_id: str) -> list[str]:
        """Return actionable recommendations based on denial patterns.

        Recommendations are prioritized by denial frequency and include
        both pattern-derived rules and general guidance.
        """
        patterns = self._engine.get_patterns(payer_id)
        if not patterns:
            return ["No denial patterns recorded for this payer yet."]

        recommendations: list[str] = []
        seen_rules: set[str] = set()

        # Sort by frequency descending so the most impactful items come first
        for p in sorted(patterns, key=lambda p: p.frequency, reverse=True):
            if p.learned_rule and p.learned_rule not in seen_rules:
                prefix = (
                    f"[{p.cdt_code} / {p.denial_reason_code} "
                    f"({p.frequency}x)] "
                )
                recommendations.append(prefix + p.learned_rule)
                seen_rules.add(p.learned_rule)

        # Add general recommendations based on aggregate analysis
        total = sum(p.frequency for p in patterns)
        preauth_denials = sum(
            p.frequency for p in patterns
            if p.denial_reason_code in ("197", "198", "39")
        )
        timely_denials = sum(
            p.frequency for p in patterns if p.denial_reason_code == "29"
        )
        coverage_denials = sum(
            p.frequency for p in patterns
            if p.denial_reason_code in ("4", "50", "96", "31")
        )

        if preauth_denials > 0 and preauth_denials / max(total, 1) > 0.15:
            rec = (
                "PRIORITY: Authorization-related denials represent "
                f"{preauth_denials}/{total} ({preauth_denials * 100 // total}%) "
                "of denials. Implement a preauthorization checklist for "
                "this payer."
            )
            if rec not in seen_rules:
                recommendations.append(rec)

        if timely_denials > 0 and timely_denials / max(total, 1) > 0.10:
            rec = (
                "PRIORITY: Timely filing denials represent "
                f"{timely_denials}/{total} ({timely_denials * 100 // total}%) "
                "of denials. Review claim submission workflow to reduce lag."
            )
            if rec not in seen_rules:
                recommendations.append(rec)

        if coverage_denials > 0 and coverage_denials / max(total, 1) > 0.20:
            rec = (
                "PRIORITY: Coverage/non-covered denials represent "
                f"{coverage_denials}/{total} ({coverage_denials * 100 // total}%) "
                "of denials. Run eligibility checks (270/271) before every visit."
            )
            if rec not in seen_rules:
                recommendations.append(rec)

        return recommendations

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _compute_trend(patterns: list[DenialPattern]) -> str:
        """Return a simple trend indicator: 'improving', 'worsening', or 'stable'.

        Compares the average frequency of patterns last seen in the most
        recent 90 days versus older patterns.
        """
        if not patterns:
            return "stable"

        today = date.today()
        recent_total = 0
        recent_count = 0
        older_total = 0
        older_count = 0

        for p in patterns:
            try:
                last = date.fromisoformat(p.last_seen)
            except (ValueError, TypeError):
                continue
            delta = (today - last).days
            if delta <= 90:
                recent_total += p.frequency
                recent_count += 1
            else:
                older_total += p.frequency
                older_count += 1

        if recent_count == 0 or older_count == 0:
            return "stable"

        recent_avg = recent_total / recent_count
        older_avg = older_total / older_count

        if recent_avg > older_avg * 1.25:
            return "worsening"
        elif recent_avg < older_avg * 0.75:
            return "improving"
        return "stable"
