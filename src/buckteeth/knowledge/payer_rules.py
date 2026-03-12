"""Payer-specific rules for frequency limits, bundling, and constraints.

Provides an in-memory repository used by the coding engine to validate
proposed codes against payer policies before submission.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FrequencyLimit:
    """How often a code may be billed for a given payer."""

    code: str
    max_per_period: int
    period_months: int
    age_min: int | None = None
    age_max: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class FrequencyCheckResult:
    """Outcome of checking whether a code is within frequency limits."""

    allowed: bool
    reason: str


@dataclass(frozen=True)
class BundlingRule:
    """Describes a bundling or mutual-exclusion constraint between codes."""

    code: str
    bundled_with: str
    rule: str  # e.g. "denied_together", "cannot_bill_together", "requires_prior"
    notes: str = ""


# ── Default frequency limits (industry standard) ───────────────────────

_DEFAULT_FREQUENCY: dict[str, FrequencyLimit] = {
    "D0120": FrequencyLimit("D0120", 2, 12, notes="periodic eval"),
    "D0150": FrequencyLimit("D0150", 1, 36, notes="comprehensive eval"),
    "D0180": FrequencyLimit("D0180", 1, 36, notes="comprehensive perio eval"),
    "D0210": FrequencyLimit("D0210", 1, 36, notes="FMX"),
    "D0272": FrequencyLimit("D0272", 2, 12, notes="bitewings 2"),
    "D0274": FrequencyLimit("D0274", 2, 12, notes="bitewings 4"),
    "D0330": FrequencyLimit("D0330", 1, 36, notes="panoramic"),
    "D1110": FrequencyLimit("D1110", 2, 12, notes="adult prophy"),
    "D1120": FrequencyLimit("D1120", 2, 12, notes="child prophy"),
    "D1206": FrequencyLimit("D1206", 2, 12, age_max=18, notes="fluoride varnish"),
    "D1351": FrequencyLimit("D1351", 1, 36, age_max=16, notes="sealant per tooth"),
    "D2740": FrequencyLimit("D2740", 1, 60, notes="ceramic crown per tooth"),
    "D2750": FrequencyLimit("D2750", 1, 60, notes="PFM crown per tooth"),
    "D4341": FrequencyLimit("D4341", 1, 24, notes="SRP 4+ teeth per quadrant"),
    "D4342": FrequencyLimit("D4342", 1, 24, notes="SRP 1-3 teeth per quadrant"),
    "D4910": FrequencyLimit("D4910", 4, 12, notes="perio maintenance"),
    "D5110": FrequencyLimit("D5110", 1, 60, notes="complete denture upper"),
    "D5120": FrequencyLimit("D5120", 1, 60, notes="complete denture lower"),
}

# ── Payer-specific overrides ────────────────────────────────────────────

_PAYER_OVERRIDES: dict[str, dict[str, FrequencyLimit]] = {
    "delta_dental": {
        "D1110": FrequencyLimit("D1110", 2, 12, notes="delta standard"),
        "D0274": FrequencyLimit("D0274", 1, 12, notes="delta limits BWs to 1x/yr"),
        "D4910": FrequencyLimit("D4910", 3, 12, notes="delta allows 3 perio maint"),
    },
    "metlife": {
        "D1110": FrequencyLimit("D1110", 2, 12, notes="metlife standard"),
        "D0274": FrequencyLimit("D0274", 2, 12, notes="metlife allows 2x/yr"),
        "D1206": FrequencyLimit("D1206", 2, 12, age_max=16, notes="metlife fluoride age 16"),
        "D2740": FrequencyLimit("D2740", 1, 120, notes="metlife crown 10-year rule"),
    },
}

# ── Bundling rules ──────────────────────────────────────────────────────

_BUNDLING_RULES: list[BundlingRule] = [
    BundlingRule(
        "D2950", "D2740", "denied_together",
        "Core buildup often denied when billed same date as crown",
    ),
    BundlingRule(
        "D2950", "D2750", "denied_together",
        "Core buildup often denied when billed same date as crown",
    ),
    BundlingRule(
        "D1110", "D4341", "cannot_bill_together",
        "Prophylaxis and SRP cannot be billed on same date",
    ),
    BundlingRule(
        "D1110", "D4342", "cannot_bill_together",
        "Prophylaxis and SRP cannot be billed on same date",
    ),
    BundlingRule(
        "D1110", "D4910", "cannot_bill_together",
        "Prophylaxis and perio maintenance cannot be billed on same date",
    ),
    BundlingRule(
        "D1206", "D1208", "cannot_bill_together",
        "Fluoride varnish and fluoride rinse cannot be billed together",
    ),
    BundlingRule(
        "D0220", "D0230", "requires_prior",
        "Additional PA (D0230) requires first PA (D0220) on same date",
    ),
    BundlingRule(
        "D0210", "D0330", "cannot_bill_together",
        "FMX and panoramic should not be billed on same date",
    ),
]


class PayerRuleRepository:
    """In-memory repository for payer-specific coding rules.

    Falls back to industry-standard defaults when a payer or code is
    not found in the override tables.
    """

    def __init__(self) -> None:
        self._defaults = dict(_DEFAULT_FREQUENCY)
        self._overrides = {k: dict(v) for k, v in _PAYER_OVERRIDES.items()}
        self._bundling = list(_BUNDLING_RULES)

    # ── public API ──────────────────────────────────────────────────────

    def get_frequency_limit(
        self, payer_id: str, cdt_code: str
    ) -> FrequencyLimit | None:
        """Return the frequency limit for a code under a specific payer.

        Checks payer-specific overrides first, then falls back to defaults.
        Returns None if no rule exists for the code.
        """
        code = cdt_code.upper().strip()
        payer = payer_id.lower().strip()

        payer_rules = self._overrides.get(payer)
        if payer_rules and code in payer_rules:
            return payer_rules[code]
        return self._defaults.get(code)

    def check_frequency(
        self,
        payer_id: str,
        cdt_code: str,
        months_since_last: int | None,
    ) -> FrequencyCheckResult:
        """Check whether a code is within the payer's frequency limit.

        Args:
            payer_id: Payer identifier.
            cdt_code: CDT code to check.
            months_since_last: Months since the code was last billed.
                If None, the code is assumed to have no prior history.

        Returns:
            FrequencyCheckResult indicating whether billing is allowed.
        """
        limit = self.get_frequency_limit(payer_id, cdt_code)
        if limit is None:
            return FrequencyCheckResult(True, "No frequency rule found; allowed by default")

        if months_since_last is None:
            return FrequencyCheckResult(True, "No prior history; allowed")

        min_interval = limit.period_months // limit.max_per_period
        if months_since_last < min_interval:
            return FrequencyCheckResult(
                False,
                f"Frequency limit: {limit.max_per_period}x per {limit.period_months} months "
                f"(minimum {min_interval} months between services). "
                f"Last billed {months_since_last} months ago.",
            )

        return FrequencyCheckResult(True, "Within frequency limits")

    def get_bundling_rules(self, cdt_code: str) -> list[BundlingRule]:
        """Return all bundling rules that involve the given code."""
        code = cdt_code.upper().strip()
        return [
            r for r in self._bundling if r.code == code or r.bundled_with == code
        ]
