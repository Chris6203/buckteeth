"""
Pre-Submission Validation Engine

Runs comprehensive checks on a claim BEFORE submission to prevent denials.
Combines:
- Payer-specific frequency rules
- Documentation completeness
- Patient history / prior service dates
- Known denial patterns for this payer
- Benefit/eligibility status (when available)

The goal: catch every preventable denial before the claim leaves the office.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from buckteeth.coding.documentation_checker import check_documentation
from buckteeth.edi.payer_directory import payer_directory


@dataclass
class ValidationIssue:
    """A single validation issue found during pre-submission check."""

    code: str  # Issue code (e.g., "FREQ_VIOLATION", "DOC_MISSING")
    severity: str  # "block" (don't submit), "warn" (submit with caution), "info"
    category: str  # "frequency", "documentation", "eligibility", "coding", "history"
    message: str
    cdt_code: str | None = None
    recommendation: str | None = None
    denial_probability: int = 0  # 0-100 estimated denial chance

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "cdt_code": self.cdt_code,
            "recommendation": self.recommendation,
            "denial_probability": self.denial_probability,
        }


@dataclass
class ValidationResult:
    """Complete pre-submission validation result."""

    issues: list[ValidationIssue] = field(default_factory=list)
    passed: bool = True
    overall_denial_risk: int = 0  # 0-100
    summary: str = ""

    @property
    def blockers(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "block"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warn"]

    @property
    def info(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "info"]

    def to_dict(self) -> dict:
        return {
            "issues": [i.to_dict() for i in self.issues],
            "passed": self.passed,
            "overall_denial_risk": self.overall_denial_risk,
            "summary": self.summary,
            "blocker_count": len(self.blockers),
            "warning_count": len(self.warnings),
        }


# Frequency rule parsing patterns
FREQUENCY_PATTERNS: dict[str, tuple[int, int]] = {
    # pattern -> (count, months)
    "1x per calendar year": (1, 12),
    "1x per 12 months": (1, 12),
    "2x per calendar year": (2, 12),
    "2x per 12 months": (2, 12),
    "1x per 6 months": (1, 6),
    "1x per 36 months": (1, 36),
    "1x per 3 years": (1, 36),
    "1x per 5 years per tooth": (1, 60),
    "1x per 5 years": (1, 60),
    "1x per 60 months per tooth": (1, 60),
    "1x per 7 years per tooth": (1, 84),
    "1x per 10 years": (1, 120),
    "1x per quadrant per 24 months": (1, 24),
    "1x per quadrant per 36 months": (1, 36),
    "lifetime benefit": (1, 999),
    "as needed": (999, 1),  # essentially unlimited
}


def parse_frequency_rule(rule: str) -> tuple[int, int] | None:
    """Parse a frequency rule string into (max_count, period_months)."""
    rule_lower = rule.lower().strip()
    for pattern, values in FREQUENCY_PATTERNS.items():
        if pattern in rule_lower:
            return values
    return None


def validate_pre_submission(
    coded_procedures: list[dict],
    payer_id: str | None = None,
    patient_history: list[dict] | None = None,
    has_images: bool = False,
    has_narrative: bool = False,
    has_perio_charting: bool = False,
    eligibility: dict | None = None,
    denial_patterns: list[dict] | None = None,
    patient_age: int | None = None,
    date_of_service: str | date | None = None,
    payer_type: str | None = None,
    secondary_insurance: dict | None = None,
) -> ValidationResult:
    """
    Run comprehensive pre-submission validation.

    Args:
        coded_procedures: List of procedure dicts with cdt_code, cdt_description,
                         tooth_number, surfaces, fee_submitted
        payer_id: Insurance payer ID for payer-specific rules
        patient_history: Prior services [{cdt_code, date_of_service, tooth_number}]
        has_images: Whether supporting images are attached
        has_narrative: Whether clinical narrative is included
        has_perio_charting: Whether periodontal charting data is available
        eligibility: Eligibility data {annual_maximum, annual_used, annual_remaining, deductible, deductible_met}
        denial_patterns: Known denial patterns for this payer [{cdt_code, reason, frequency}]
        patient_age: Patient age in years (used for age limitation checks)
        date_of_service: Date of service for timely filing checks (str "YYYY-MM-DD" or date)
        payer_type: Payer type for timely filing rules ("commercial", "medicaid", "medicare")
        secondary_insurance: Secondary insurance info dict, if any (for COB checks)

    Returns:
        ValidationResult with all issues found
    """
    issues: list[ValidationIssue] = []
    today = date.today()
    patient_history = patient_history or []
    denial_patterns = denial_patterns or []

    # Normalize date_of_service to a date object
    dos: date | None = None
    if date_of_service is not None:
        if isinstance(date_of_service, str):
            try:
                dos = datetime.strptime(date_of_service, "%Y-%m-%d").date()
            except ValueError:
                dos = None
        elif isinstance(date_of_service, date):
            dos = date_of_service

    # ── 1. Documentation Completeness ────────────────────────────────
    doc_check = check_documentation(
        coded_procedures=coded_procedures,
        has_images=has_images,
        has_narrative=has_narrative,
        has_perio_charting=has_perio_charting,
    )
    for alert in doc_check.alerts:
        issues.append(ValidationIssue(
            code="DOC_MISSING",
            severity="block" if alert.severity == "required" else "warn",
            category="documentation",
            message=f"Missing {alert.label} for {alert.cdt_code}",
            cdt_code=alert.cdt_code,
            recommendation=alert.description,
            denial_probability=80 if alert.severity == "required" else 30,
        ))

    # ── 1b. SRP-specific documentation check ────────────────────────
    for proc in coded_procedures:
        code = proc.get("cdt_code", "")
        if code in ("D4341", "D4342") and not has_perio_charting:
            issues.append(ValidationIssue(
                code="SRP_NO_PERIO_CHARTING",
                severity="block",
                category="documentation",
                message=f"SRP ({code}) submitted without periodontal charting data.",
                cdt_code=code,
                recommendation="SRP claims without periodontal charting (pocket depths, "
                               "bleeding points, bone loss) are denied 40%+ of the time. "
                               "Attach full perio charting before submitting.",
                denial_probability=90,
            ))

    # ── 1c. Crown-specific narrative guidance ────────────────────────
    for proc in coded_procedures:
        code = proc.get("cdt_code", "")
        if code and code >= "D2740" and code <= "D2799":
            issues.append(ValidationIssue(
                code="CROWN_NARRATIVE_REMINDER",
                severity="info",
                category="documentation",
                message=f"Crown ({code}): ensure narrative addresses required clinical details.",
                cdt_code=code,
                recommendation="Crown narrative should include: percentage of tooth structure "
                               "compromised, reason existing restoration failed, and why "
                               "alternative treatments are not viable.",
                denial_probability=15,
            ))

    # ── 2. Payer Frequency Rules ─────────────────────────────────────
    payer = payer_directory.lookup(payer_id) if payer_id else None

    if payer:
        for proc in coded_procedures:
            code = proc.get("cdt_code", "")
            tooth = proc.get("tooth_number")
            rule_text = payer.frequency_rules.get(code)

            if not rule_text:
                continue

            freq = parse_frequency_rule(rule_text)
            if not freq:
                continue

            max_count, period_months = freq
            if max_count >= 999:
                continue  # unlimited

            # Check patient history for this code within the period
            cutoff = today - timedelta(days=period_months * 30)
            prior_count = 0
            for hist in patient_history:
                if hist.get("cdt_code") != code:
                    continue
                hist_date = hist.get("date_of_service", "")
                if isinstance(hist_date, str) and hist_date:
                    try:
                        d = datetime.strptime(hist_date, "%Y-%m-%d").date()
                        if d >= cutoff:
                            # For tooth-specific rules, check tooth match
                            if "per tooth" in (rule_text or ""):
                                if hist.get("tooth_number") == tooth:
                                    prior_count += 1
                            else:
                                prior_count += 1
                    except ValueError:
                        pass

            if prior_count >= max_count:
                issues.append(ValidationIssue(
                    code="FREQ_VIOLATION",
                    severity="block",
                    category="frequency",
                    message=f"{code} exceeds {payer.short_name or payer.name} frequency limit: {rule_text}. "
                            f"Patient has had {prior_count} in the last {period_months} months.",
                    cdt_code=code,
                    recommendation=f"Check patient's last {code} date. If within {period_months} months, "
                                   "this will likely be denied. Consider waiting or requesting an exception.",
                    denial_probability=95,
                ))

        # ── 3. Pre-Authorization Check ───────────────────────────────
        for proc in coded_procedures:
            code = proc.get("cdt_code", "")
            if code in payer.preauth_required_codes:
                issues.append(ValidationIssue(
                    code="PREAUTH_REQUIRED",
                    severity="warn",
                    category="eligibility",
                    message=f"{code} typically requires pre-authorization from {payer.short_name or payer.name}.",
                    cdt_code=code,
                    recommendation="Submit a predetermination (D9310) before proceeding, or verify "
                                   "pre-auth was already obtained.",
                    denial_probability=60,
                ))

    # ── 4. Eligibility / Benefit Checks ──────────────────────────────
    if eligibility:
        total_fees = sum(proc.get("fee_submitted", 0) or 0 for proc in coded_procedures)
        remaining = eligibility.get("annual_remaining")
        deductible_met = eligibility.get("deductible_met")

        if remaining is not None and total_fees > remaining:
            issues.append(ValidationIssue(
                code="BENEFIT_EXCEEDED",
                severity="warn",
                category="eligibility",
                message=f"Total fees (${total_fees:.2f}) exceed remaining annual benefit "
                        f"(${remaining:.2f}). Patient may owe ${total_fees - remaining:.2f}.",
                recommendation="Inform patient of expected out-of-pocket cost before treatment. "
                               "Consider splitting treatment across benefit years if possible.",
                denial_probability=40,
            ))

        if deductible_met is False:
            deductible = eligibility.get("deductible", 0)
            issues.append(ValidationIssue(
                code="DEDUCTIBLE_NOT_MET",
                severity="info",
                category="eligibility",
                message=f"Patient's deductible (${deductible:.2f}) has not been met. "
                        "Payment may be reduced.",
                recommendation="Patient will be responsible for deductible amount before "
                               "insurance coverage applies.",
                denial_probability=0,
            ))

    # ── 5. Known Denial Patterns ─────────────────────────────────────
    for proc in coded_procedures:
        code = proc.get("cdt_code", "")
        for pattern in denial_patterns:
            if pattern.get("cdt_code") == code and pattern.get("frequency", 0) >= 2:
                issues.append(ValidationIssue(
                    code="DENIAL_PATTERN",
                    severity="warn",
                    category="history",
                    message=f"{code} has been denied {pattern['frequency']} times by this payer: "
                            f"{pattern.get('reason', 'unknown reason')}",
                    cdt_code=code,
                    recommendation=pattern.get("learned_rule") or
                                   "Review prior denials for this code and strengthen documentation.",
                    denial_probability=min(90, 40 + pattern["frequency"] * 10),
                ))

    # ── 6. Basic Coding Checks ───────────────────────────────────────
    cdt_codes = [p.get("cdt_code", "") for p in coded_procedures]

    # Check for common bundling issues
    # Format: (codes_present, codes_conflict, message, severity, denial_probability)
    # "present + conflict" means both are on the claim and may cause issues.
    # For the original pattern (present WITHOUT conflict), see the separate loop below.
    bundling_checks_both_present = [
        ({"D2950"}, {"D2740", "D2750"},
         "Core buildup (D2950) + crown same day — some payers bundle these together. "
         "Verify payer allows separate billing before submitting.",
         "warn", 35),
        ({"D0220"}, {"D0210"},
         "Periapical X-ray (D0220) is included in full-mouth series (D0210). "
         "PA will likely be denied when billed same day as FMX.",
         "warn", 70),
        ({"D0274"}, {"D0210"},
         "Bitewing X-rays (D0274) are included in full-mouth series (D0210). "
         "BWX will likely be denied when billed same day as FMX.",
         "warn", 70),
        ({"D1110"}, {"D4910"},
         "Prophy (D1110) and perio maintenance (D4910) cannot be billed same day. "
         "Use one or the other based on patient's periodontal status.",
         "block", 95),
        ({"D1110"}, {"D4341"},
         "Prophy (D1110) and SRP (D4341) cannot be billed same day. "
         "SRP replaces the prophylaxis for periodontal patients.",
         "block", 95),
        ({"D4341"}, {"D4355"},
         "SRP (D4341) and full mouth debridement (D4355) should not be billed same visit. "
         "Debridement should precede SRP by at least 4 weeks.",
         "block", 90),
        ({"D9310"}, {"D0150"},
         "Consultation (D9310) and comprehensive eval (D0150) same day — some payers "
         "bundle these together. Verify payer policy.",
         "warn", 40),
    ]

    code_set = set(cdt_codes)

    for check_codes, conflict_codes, message, severity, prob in bundling_checks_both_present:
        if check_codes & code_set and conflict_codes & code_set:
            issues.append(ValidationIssue(
                code="BUNDLING_RISK",
                severity=severity,
                category="coding",
                message=message,
                cdt_code=", ".join(check_codes & code_set),
                denial_probability=prob,
            ))

    # "present WITHOUT related code" checks (original pattern)
    bundling_checks_missing = [
        ({"D2950", "D2952"}, {"D2740", "D2750", "D2751", "D2790", "D2791", "D2792"},
         "Core buildup without a crown — some payers bundle these or deny standalone core buildups."),
    ]

    for check_codes, requires_codes, message in bundling_checks_missing:
        if check_codes & code_set and not (requires_codes & code_set):
            issues.append(ValidationIssue(
                code="BUNDLING_RISK",
                severity="info",
                category="coding",
                message=message,
                cdt_code=", ".join(check_codes & code_set),
                denial_probability=25,
            ))

    # D9215 local anesthesia billed separately — most payers include in procedure
    if "D9215" in code_set:
        issues.append(ValidationIssue(
            code="BUNDLING_RISK",
            severity="warn",
            category="coding",
            message="Local anesthesia (D9215) billed separately — most payers consider "
                    "anesthesia included in the procedure fee and will deny D9215.",
            cdt_code="D9215",
            recommendation="Verify payer allows separate billing for D9215 before submitting.",
            denial_probability=75,
        ))

    # D2940 protective restoration + permanent restoration same tooth same day
    if "D2940" in code_set:
        perm_restore_codes = {c for c in code_set if c.startswith("D2") and c != "D2940"
                              and c >= "D2000" and c <= "D2999"}
        if perm_restore_codes:
            # Check for same-tooth overlap
            d2940_teeth = {p.get("tooth_number") for p in coded_procedures
                          if p.get("cdt_code") == "D2940" and p.get("tooth_number")}
            perm_teeth = {p.get("tooth_number") for p in coded_procedures
                         if p.get("cdt_code") in perm_restore_codes and p.get("tooth_number")}
            overlap = d2940_teeth & perm_teeth
            if overlap:
                issues.append(ValidationIssue(
                    code="BUNDLING_RISK",
                    severity="warn",
                    category="coding",
                    message=f"Protective restoration (D2940) and permanent restoration on the "
                            f"same tooth ({', '.join(str(t) for t in sorted(overlap))}) same day — "
                            "payers will deny the temporary when a permanent restoration is placed.",
                    cdt_code="D2940",
                    denial_probability=85,
                ))

    # D7140 extraction + D7210 surgical extraction same tooth
    if "D7140" in code_set and "D7210" in code_set:
        d7140_teeth = {p.get("tooth_number") for p in coded_procedures
                       if p.get("cdt_code") == "D7140" and p.get("tooth_number")}
        d7210_teeth = {p.get("tooth_number") for p in coded_procedures
                       if p.get("cdt_code") == "D7210" and p.get("tooth_number")}
        overlap = d7140_teeth & d7210_teeth
        if overlap:
            issues.append(ValidationIssue(
                code="BUNDLING_RISK",
                severity="block",
                category="coding",
                message=f"Simple extraction (D7140) and surgical extraction (D7210) on the same "
                        f"tooth ({', '.join(str(t) for t in sorted(overlap))}) — an extraction "
                        "cannot be both simple and surgical. Use one code.",
                cdt_code="D7140, D7210",
                recommendation="Choose D7140 (simple) or D7210 (surgical) based on the actual "
                               "procedure performed. Billing both on the same tooth will be denied.",
                denial_probability=100,
            ))

    # ── 7. Age Limitation Checks ─────────────────────────────────────
    if patient_age is not None:
        age_checks = [
            # (codes_or_range, max_age, min_age, message)
            ({"D1351"}, 16, None,
             "Sealants (D1351) are typically covered only for patients under 16 "
             "(some plans cap at 14). Patient is {age}."),
            ({"D1120"}, 14, None,
             "Child prophylaxis (D1120) is intended for patients under 14. "
             "Patient is {age}. Use D1110 (adult prophy) instead."),
            ({"D1110"}, None, 14,
             "Adult prophylaxis (D1110) is intended for patients 14 and older. "
             "Patient is {age}. Use D1120 (child prophy) instead."),
            ({"D8080"}, 19, None,
             "Comprehensive orthodontic treatment — adolescent (D8080) is typically "
             "covered for patients under 19. Patient is {age}."),
        ]

        for check_codes, max_age, min_age, msg_template in age_checks:
            if check_codes & code_set:
                flagged = False
                if max_age is not None and patient_age >= max_age:
                    flagged = True
                if min_age is not None and patient_age < min_age:
                    flagged = True
                if flagged:
                    issues.append(ValidationIssue(
                        code="AGE_LIMITATION",
                        severity="warn",
                        category="coding",
                        message=msg_template.format(age=patient_age),
                        cdt_code=", ".join(check_codes & code_set),
                        recommendation="Verify patient's plan covers this procedure for their "
                                       "age group. Consider using the age-appropriate code.",
                        denial_probability=60,
                    ))

        # Stainless steel crowns D2930-D2934
        ss_crown_codes = {c for c in code_set if c >= "D2930" and c <= "D2934"}
        if ss_crown_codes and patient_age >= 14:
            issues.append(ValidationIssue(
                code="AGE_LIMITATION",
                severity="warn",
                category="coding",
                message=f"Stainless steel crowns ({', '.join(sorted(ss_crown_codes))}) are "
                        f"typically covered for patients under 14. Patient is {patient_age}.",
                cdt_code=", ".join(sorted(ss_crown_codes)),
                recommendation="Verify payer covers stainless steel crowns for adult patients. "
                               "Most plans limit SSCs to pediatric patients.",
                denial_probability=55,
            ))

        # Space maintainers D1510-D1575
        space_maint_codes = {c for c in code_set if c >= "D1510" and c <= "D1575"}
        if space_maint_codes and patient_age >= 14:
            issues.append(ValidationIssue(
                code="AGE_LIMITATION",
                severity="warn",
                category="coding",
                message=f"Space maintainers ({', '.join(sorted(space_maint_codes))}) are "
                        f"typically covered for patients under 14. Patient is {patient_age}.",
                cdt_code=", ".join(sorted(space_maint_codes)),
                recommendation="Verify payer covers space maintainers for this age group.",
                denial_probability=55,
            ))

    # ── 8. Timely Filing Check ───────────────────────────────────────
    if dos is not None:
        days_since_service = (today - dos).days

        # Determine filing deadline based on payer type
        filing_deadlines = {
            "commercial": 180,
            "medicaid": 90,
            "medicare": 365,
        }
        ptype = (payer_type or "commercial").lower()
        deadline_days = filing_deadlines.get(ptype, 180)

        days_remaining = deadline_days - days_since_service

        if days_remaining < 0:
            issues.append(ValidationIssue(
                code="TIMELY_FILING_EXPIRED",
                severity="block",
                category="eligibility",
                message=f"Timely filing deadline has passed. Date of service was {dos} "
                        f"({days_since_service} days ago). {ptype.title()} deadline is "
                        f"{deadline_days} days.",
                recommendation="This claim will almost certainly be denied for untimely filing. "
                               "Contact the payer to request a filing extension if extenuating "
                               "circumstances apply.",
                denial_probability=98,
            ))
        elif days_remaining <= 30:
            issues.append(ValidationIssue(
                code="TIMELY_FILING_URGENT",
                severity="warn",
                category="eligibility",
                message=f"Timely filing deadline approaching. Date of service was {dos} "
                        f"({days_since_service} days ago). Only {days_remaining} days "
                        f"remaining before the {ptype.title()} deadline of {deadline_days} days.",
                recommendation="Submit this claim immediately to avoid a timely filing denial.",
                denial_probability=30,
            ))
        elif days_remaining <= 60:
            issues.append(ValidationIssue(
                code="TIMELY_FILING_WARNING",
                severity="info",
                category="eligibility",
                message=f"Timely filing note: {days_remaining} days remaining before the "
                        f"{ptype.title()} filing deadline ({deadline_days} days from "
                        f"date of service {dos}).",
                recommendation="Plan to submit this claim soon to allow time for any "
                               "resubmissions if needed.",
                denial_probability=5,
            ))

    # ── 9. Waiting Period Awareness ──────────────────────────────────
    # Major procedures — remind practice to verify waiting periods
    major_proc_codes = {c for c in code_set
                        if (c >= "D2740" and c <= "D2799")   # crowns
                        or (c >= "D6200" and c <= "D6999")   # bridges/pontics
                        or (c >= "D5110" and c <= "D5899")}  # dentures/partials
    if major_proc_codes:
        issues.append(ValidationIssue(
            code="WAITING_PERIOD_REMINDER",
            severity="info",
            category="eligibility",
            message="Major procedures (crowns, bridges, dentures) often have a 12-month "
                    "waiting period on new insurance plans.",
            cdt_code=", ".join(sorted(major_proc_codes)[:3]) + (
                "..." if len(major_proc_codes) > 3 else ""),
            recommendation="Verify the patient's plan effective date and confirm any waiting "
                           "period for major services has been satisfied before proceeding.",
            denial_probability=10,
        ))

    ortho_codes = {c for c in code_set if c >= "D8000" and c <= "D8999"}
    if ortho_codes:
        issues.append(ValidationIssue(
            code="WAITING_PERIOD_REMINDER",
            severity="info",
            category="eligibility",
            message="Orthodontic treatment often has a 12-24 month waiting period on "
                    "new insurance plans.",
            cdt_code=", ".join(sorted(ortho_codes)[:3]) + (
                "..." if len(ortho_codes) > 3 else ""),
            recommendation="Verify the patient's plan effective date and confirm the "
                           "orthodontic waiting period has been satisfied.",
            denial_probability=10,
        ))

    # ── 10. Missing Tooth Clause Awareness ───────────────────────────
    bridge_pontic_codes = {c for c in code_set
                           if (c >= "D6210" and c <= "D6252")
                           or (c >= "D6710" and c <= "D6794")}
    if bridge_pontic_codes:
        issues.append(ValidationIssue(
            code="MISSING_TOOTH_CLAUSE",
            severity="info",
            category="eligibility",
            message="Bridge/pontic codes present — many plans have a missing tooth clause. "
                    "The tooth must have been extracted AFTER the policy effective date for "
                    "the replacement to be covered.",
            cdt_code=", ".join(sorted(bridge_pontic_codes)[:3]) + (
                "..." if len(bridge_pontic_codes) > 3 else ""),
            recommendation="Verify the date the missing tooth was extracted and confirm it "
                           "falls after the patient's current policy effective date. Include "
                           "extraction date in the claim narrative.",
            denial_probability=20,
        ))

    denture_codes = {c for c in code_set
                     if (c >= "D5110" and c <= "D5140")
                     or (c >= "D5211" and c <= "D5214")}
    if denture_codes:
        issues.append(ValidationIssue(
            code="MISSING_TOOTH_CLAUSE",
            severity="info",
            category="eligibility",
            message="Denture codes present — many plans have a missing tooth clause. "
                    "Teeth must have been extracted AFTER the policy effective date for "
                    "the prosthetic to be covered.",
            cdt_code=", ".join(sorted(denture_codes)),
            recommendation="Verify the extraction dates for all missing teeth and confirm they "
                           "fall after the patient's current policy effective date.",
            denial_probability=20,
        ))

    # ── 11. Coordination of Benefits (COB) Check ─────────────────────
    if secondary_insurance:
        issues.append(ValidationIssue(
            code="COB_REMINDER",
            severity="info",
            category="eligibility",
            message="Patient has secondary insurance on file. Coordination of benefits (COB) "
                    "applies — submit to primary first, then secondary with the primary EOB.",
            recommendation="Ensure the primary claim is adjudicated before submitting to the "
                           "secondary payer. Include the primary payer's EOB/remittance with "
                           "the secondary claim. Verify COB provisions for both plans.",
            denial_probability=5,
        ))

    # ── Calculate Overall Risk ───────────────────────────────────────
    if not issues:
        overall_risk = 5  # baseline
        summary = "All checks passed. Low denial risk."
    else:
        # Weighted average of denial probabilities
        weights = {"block": 3, "warn": 2, "info": 1}
        weighted_sum = sum(
            i.denial_probability * weights.get(i.severity, 1) for i in issues
        )
        total_weight = sum(weights.get(i.severity, 1) for i in issues)
        overall_risk = min(95, weighted_sum // total_weight if total_weight else 10)

        blockers = [i for i in issues if i.severity == "block"]
        warnings = [i for i in issues if i.severity == "warn"]

        if blockers:
            summary = (
                f"{len(blockers)} issue(s) should be resolved before submission. "
                f"Estimated denial risk: {overall_risk}%."
            )
        elif warnings:
            summary = (
                f"{len(warnings)} warning(s) found. Review recommended before submission. "
                f"Estimated denial risk: {overall_risk}%."
            )
        else:
            summary = f"Minor notes found. Estimated denial risk: {overall_risk}%."

    passed = len([i for i in issues if i.severity == "block"]) == 0

    return ValidationResult(
        issues=issues,
        passed=passed,
        overall_denial_risk=overall_risk,
        summary=summary,
    )
