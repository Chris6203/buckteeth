"""Dental insurance payer directory with EDI payer IDs and billing rules.

Provides a lookup directory of major dental insurance payers with their
EDI identifiers, claim filing indicators, frequency limitations,
preauthorization requirements, and common denial codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Payer:
    """A dental insurance payer with EDI and billing metadata."""

    payer_id: str
    name: str
    short_name: str
    edi_payer_id: str
    claim_filing_indicator: str  # CI=commercial, MB=Medicare, MC=Medicaid, CH=TRICARE
    eligibility_supported: bool = True
    era_supported: bool = True
    frequency_rules: dict[str, str] = field(default_factory=dict)
    preauth_required_codes: list[str] = field(default_factory=list)
    common_denial_codes: list[str] = field(default_factory=list)
    alternate_payer_ids: list[str] = field(default_factory=list)  # Other IDs this payer uses
    verified: bool = False  # Whether payer_id has been verified against official sources
    notes: str = ""


class PayerDirectory:
    """Registry of dental insurance payers, searchable by ID or name."""

    def __init__(self) -> None:
        self._payers: dict[str, Payer] = {}
        self._load_payers()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, payer_id: str) -> Payer | None:
        """Return a payer by exact ``payer_id`` or alternate ID, or ``None``."""
        result = self._payers.get(payer_id)
        if result:
            return result
        # Check alternate IDs
        for payer in self._payers.values():
            if payer_id in payer.alternate_payer_ids:
                return payer
        return None

    def search(self, query: str) -> list[Payer]:
        """Return payers whose name or short_name matches *query* (case-insensitive, bidirectional).

        Also matches when every significant word in the payer's short_name
        appears in the query (e.g. "Delta Dental Premier" matches "Delta CA"
        because the core identifier words overlap).
        """
        q = query.lower()
        _stop = {"of", "the", "and", "a", "an", "in", "for"}
        q_words = set(q.split()) - _stop

        def _matches(p: Payer) -> bool:
            if q in p.name.lower() or p.name.lower() in q:
                return True
            if q in p.short_name.lower() or p.short_name.lower() in q:
                return True
            if q in p.payer_id.lower() or q in p.edi_payer_id.lower():
                return True
            # Word-overlap: check if the core identifying words overlap enough
            name_words = set(p.name.lower().split()) - _stop
            overlap = q_words & name_words
            # Match if at least 2 significant words overlap (e.g. "delta" + "dental")
            if len(overlap) >= 2:
                return True
            return False

        return [p for p in self._payers.values() if _matches(p)]

    def list_all(self) -> list[Payer]:
        """Return every payer in the directory, sorted by name."""
        return sorted(self._payers.values(), key=lambda p: p.name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add(self, payer: Payer) -> None:
        self._payers[payer.payer_id] = payer

    def _load_payers(self) -> None:  # noqa: C901 (long but straightforward data)
        # ---------------------------------------------------------------
        # Common frequency-rule templates
        # ---------------------------------------------------------------
        _std_frequency: dict[str, str] = {
            "D0120": "2x per calendar year",
            "D0150": "1x per 36 months",
            "D0210": "1x per 36 months",
            "D0220": "as needed",
            "D0230": "as needed",
            "D0274": "1x per calendar year",
            "D0330": "1x per 36 months",
            "D1110": "2x per calendar year",
            "D1120": "2x per calendar year",
            "D1206": "2x per calendar year for patients under 19",
            "D1208": "1x per calendar year",
            "D1351": "1x per tooth per lifetime for patients under 16",
            "D2140": "1x per 24 months per surface per tooth",
            "D2150": "1x per 24 months per surface per tooth",
            "D2160": "1x per 24 months per surface per tooth",
            "D2161": "1x per 24 months per surface per tooth",
            "D2330": "1x per 24 months per surface per tooth",
            "D2331": "1x per 24 months per surface per tooth",
            "D2332": "1x per 24 months per surface per tooth",
            "D2391": "1x per 24 months per surface per tooth",
            "D2392": "1x per 24 months per surface per tooth",
            "D2393": "1x per 24 months per surface per tooth",
            "D2394": "1x per 24 months per surface per tooth",
            "D2740": "1x per 5 years per tooth",
            "D2750": "1x per 5 years per tooth",
            "D2751": "1x per 5 years per tooth",
            "D2752": "1x per 5 years per tooth",
            "D4341": "1x per quadrant per 24 months",
            "D4342": "1x per quadrant per 24 months",
            "D4910": "4x per calendar year after active perio therapy",
            "D5110": "1x per 5 years",
            "D5120": "1x per 5 years",
            "D5213": "1x per 5 years",
            "D5214": "1x per 5 years",
            "D7140": "as needed",
            "D7210": "as needed",
            "D7230": "as needed",
            "D7240": "as needed",
            "D8080": "lifetime benefit",
        }

        def _freq(**overrides: str) -> dict[str, str]:
            """Return standard frequency rules with optional overrides."""
            merged = dict(_std_frequency)
            merged.update(overrides)
            return merged

        # ---------------------------------------------------------------
        # Delta Dental plans
        # ---------------------------------------------------------------
        self._add(Payer(
            payer_id="DDCA1",
            name="Delta Dental of California",
            short_name="Delta CA",
            edi_payer_id="DDCA1",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751", "D2752",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes="Largest Delta Dental affiliate. PPO and Premier networks.",
        ))

        self._add(Payer(
            payer_id="83028",
            name="Delta Dental of New York",
            short_name="Delta NY",
            edi_payer_id="83028",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="2x per benefit year",
                D0274="1x per benefit year",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "197"],
            notes="Uses benefit year rather than calendar year for frequency.",
        ))

        self._add(Payer(
            payer_id="23159",
            name="Delta Dental of Pennsylvania",
            short_name="Delta PA",
            edi_payer_id="23159",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "119", "197"],
            notes="Also administers Delta Dental of Delaware.",
        ))

        self._add(Payer(
            payer_id="DDTX1",
            name="Delta Dental of Texas",
            short_name="Delta TX",
            edi_payer_id="DDTX1",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D4341="1x per quadrant per 36 months",
                D4342="1x per quadrant per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="36-month SRP limitation. Preauth strongly recommended for crowns.",
        ))

        self._add(Payer(
            payer_id="43090",
            name="Delta Dental of Illinois",
            short_name="Delta IL",
            edi_payer_id="43090",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "96", "119", "197"],
            notes="Administers plans for several Midwest states.",
        ))

        self._add(Payer(
            payer_id="DDWA1",
            name="Delta Dental of Washington",
            short_name="Delta WA",
            edi_payer_id="DDWA1",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0210="1x per 60 months",
                D0330="1x per 60 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96"],
            notes="60-month FMX limitation. Also covers Alaska and Oregon.",
        ))

        self._add(Payer(
            payer_id="83026",
            name="Delta Dental of Michigan",
            short_name="Delta MI",
            edi_payer_id="83026",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="Ohio and Indiana groups may also route here.",
        ))

        self._add(Payer(
            payer_id="83021",
            name="Delta Dental of Massachusetts",
            short_name="Delta MA",
            edi_payer_id="83021",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1351="1x per tooth per lifetime for patients under 14",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "197"],
            notes="Sealant age limit is 14, not 16.",
        ))

        # ---------------------------------------------------------------
        # Major national dental payers
        # ---------------------------------------------------------------
        self._add(Payer(
            payer_id="61109",
            name="MetLife Dental",
            short_name="MetLife",
            edi_payer_id="61109",
            alternate_payer_ids=["65978"],
            verified=True,
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
                D0210="1x per 60 months",
                D0330="1x per 60 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751", "D2752",
                "D5110", "D5120", "D5213", "D5214",
                "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes="PDP Plus network. Voluntary preauth available for most major services.",
        ))

        self._add(Payer(
            payer_id="62308",
            name="Cigna Dental",
            short_name="Cigna",
            edi_payer_id="62308",
            verified=True,
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D2740="1x per 5 years per tooth",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="Uses 6-month interval rather than calendar year for preventive.",
        ))

        self._add(Payer(
            payer_id="60054",
            name="Aetna Dental",
            short_name="Aetna",
            edi_payer_id="60054",
            alternate_payer_ids=["68246"],  # 68246 for Aetna DMO plans
            verified=True,
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D4910="2x per calendar year after active perio therapy",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "197"],
            notes="DMO and PPO plans. Perio maintenance limited to 2x/year on many plans.",
        ))

        self._add(Payer(
            payer_id="63959",
            name="Guardian Dental",
            short_name="Guardian",
            edi_payer_id="63959",
            alternate_payer_ids=["GI813"],
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="DentalGuard Preferred network. Bitewing frequency varies by plan.",
        ))

        self._add(Payer(
            payer_id="87726",
            name="UnitedHealthcare Dental",
            short_name="UHC Dental",
            edi_payer_id="87726",
            verified=True,
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D2740="1x per 5 years per tooth",
                D4341="1x per quadrant per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes="Dual network (Options PPO and Dental Advantage). 36-month SRP.",
        ))

        self._add(Payer(
            payer_id="61101",
            name="Humana Dental",
            short_name="Humana",
            edi_payer_id="61101",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
                D4910="3x per calendar year after active perio therapy",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="CompleteDental and Preventive Plus plans. Perio maint 3x/year.",
        ))

        self._add(Payer(
            payer_id="61271",
            name="Principal Financial Dental",
            short_name="Principal",
            edi_payer_id="61271",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96"],
            notes="Voluntary preauth encouraged. Generally follows ADA guidelines.",
        ))

        self._add(Payer(
            payer_id="65056",
            name="Ameritas Dental",
            short_name="Ameritas",
            edi_payer_id="65056",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
                D4341="1x per quadrant per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "197"],
            notes="Classic and Prime Star networks. 36-month SRP and bitewing limits.",
        ))

        self._add(Payer(
            payer_id="65595",
            name="Lincoln Financial Dental",
            short_name="Lincoln Financial",
            edi_payer_id="65595",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "119"],
            notes="Lincoln DentalConnect PPO network.",
        ))

        self._add(Payer(
            payer_id="80314",
            name="Sun Life Financial Dental",
            short_name="Sun Life",
            edi_payer_id="80314",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D0274="1x per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96"],
            notes="Sun Life Dental Network. Acquired DentaQuest in 2022.",
        ))

        self._add(Payer(
            payer_id="81578",
            name="GEHA Dental",
            short_name="GEHA",
            edi_payer_id="81578",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="2x per benefit year",
                D0120="2x per benefit year",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "197"],
            notes="Federal employee dental plan. Connection Dental PPO network.",
        ))

        self._add(Payer(
            payer_id="47198",
            name="Anthem BCBS Dental",
            short_name="Anthem Dental",
            edi_payer_id="47198",
            claim_filing_indicator="CI",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751", "D2752",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes=(
                "Default payer ID 47198; actual ID varies by state. "
                "6-month interval for preventive services."
            ),
        ))

        self._add(Payer(
            payer_id="15460",
            name="DentaQuest",
            short_name="DentaQuest",
            edi_payer_id="15460",
            claim_filing_indicator="MC",
            eligibility_supported=True,
            era_supported=True,
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D2740="1x per 7 years per tooth",
                D2750="1x per 7 years per tooth",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D4341", "D4342",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes=(
                "Major Medicaid dental administrator. "
                "Preauth required for most restorative and prosthetic services."
            ),
        ))

        self._add(Payer(
            payer_id="MCNA1",
            name="MCNA Dental",
            short_name="MCNA",
            edi_payer_id="MCNA1",
            claim_filing_indicator="MC",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D2740="1x per 7 years per tooth",
                D2750="1x per 7 years per tooth",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D4341", "D4342",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="Medicaid and CHIP dental plan administrator in multiple states.",
        ))

        self._add(Payer(
            payer_id="13193",
            name="Liberty Dental Plan",
            short_name="Liberty Dental",
            edi_payer_id="13193",
            claim_filing_indicator="MC",
            frequency_rules=_freq(
                D1110="1x per 6 months",
                D0120="1x per 6 months",
                D2740="1x per 7 years per tooth",
                D2750="1x per 7 years per tooth",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D4341", "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes="Medicaid managed care dental in CA, FL, NJ, NV, and other states.",
        ))

        self._add(Payer(
            payer_id="55271",
            name="Dental Health Alliance",
            short_name="DHA",
            edi_payer_id="55271",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96"],
            notes="PPO network used by many self-funded employer groups.",
        ))

        self._add(Payer(
            payer_id="11402",
            name="Connection Dental",
            short_name="Connection Dental",
            edi_payer_id="11402",
            claim_filing_indicator="CI",
            frequency_rules=_freq(),
            preauth_required_codes=[
                "D2740", "D2750", "D2751",
                "D5110", "D5120",
                "D7210", "D7230", "D7240",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119"],
            notes="PPO network for federal employee and group plans.",
        ))

        self._add(Payer(
            payer_id="99726",
            name="TRICARE Dental Program",
            short_name="TRICARE Dental",
            edi_payer_id="99726",
            claim_filing_indicator="CH",
            frequency_rules=_freq(
                D1110="2x per benefit year",
                D0120="2x per benefit year",
                D0274="1x per benefit year",
                D2740="1x per 5 years per tooth",
                D4341="1x per quadrant per 36 months",
            ),
            preauth_required_codes=[
                "D2740", "D2750", "D2751", "D2752",
                "D5110", "D5120", "D5213", "D5214",
                "D7210", "D7230", "D7240",
                "D4341", "D4342",
                "D8080",
            ],
            common_denial_codes=["4", "29", "45", "50", "96", "119", "197"],
            notes=(
                "Active-duty family member dental benefit. "
                "Administered by United Concordia. Preauth required for most major services."
            ),
        ))


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------
payer_directory = PayerDirectory()
