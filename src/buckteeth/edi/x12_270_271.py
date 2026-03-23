"""X12 270/271 Eligibility Request/Response for dental insurance.

Generates X12 270 (Eligibility Inquiry) transactions and parses X12 271
(Eligibility/Benefit Response) transactions with full support for dental-specific
service type codes and benefit structures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Dental-specific service type codes
# ---------------------------------------------------------------------------
DENTAL_SERVICE_TYPE_CODES: dict[str, str] = {
    "30": "Dental Care",
    "23": "Diagnostic (D0100-D0999)",
    "24": "Preventive (D1000-D1999)",
    "25": "Restorative (D2000-D2999)",
    "26": "Endodontics (D3000-D3999)",
    "27": "Periodontics (D4000-D4999)",
    "28": "Prosthodontics (D5000-D5999)",
    "35": "Dental Crowns (D2700-D2799)",
    "36": "Dental Implants",
    "37": "Orthodontics (D8000-D8999)",
    "38": "Oral Surgery (D7000-D7999)",
}


# ---------------------------------------------------------------------------
# 270 – Eligibility Request
# ---------------------------------------------------------------------------
@dataclass
class EligibilityRequest:
    """Data required to build an X12 270 eligibility inquiry."""

    subscriber_id: str
    subscriber_first_name: str
    subscriber_last_name: str
    subscriber_dob: date
    payer_id: str
    payer_name: str
    provider_npi: str
    provider_name: str
    date_of_service: date
    service_type_codes: list[str] = field(default_factory=lambda: ["30"])


class X12_270_Generator:
    """Generates X12 270 (Eligibility Inquiry) transactions.

    Follows the ASC X12 005010X279A1 implementation guide.  Output uses ``~``
    as the segment terminator and ``*`` as the element separator by default.
    """

    def __init__(
        self,
        element_sep: str = "*",
        segment_term: str = "~",
        sub_element_sep: str = ":",
    ) -> None:
        self._el = element_sep
        self._st = segment_term
        self._sub = sub_element_sep

    # -- helpers ------------------------------------------------------------

    def _seg(self, *elements: str) -> str:
        """Build a single segment string (without trailing terminator)."""
        return self._el.join(elements)

    def _line(self, *elements: str) -> str:
        return self._seg(*elements) + self._st

    @staticmethod
    def _control_number() -> str:
        """Generate a control number from the current timestamp."""
        return datetime.utcnow().strftime("%y%m%d%H%M%S%f")[:9]

    # -- public API ---------------------------------------------------------

    def generate(self, request: EligibilityRequest) -> str:
        """Return a complete X12 270 transaction as a string."""
        ctrl = self._control_number()
        today = datetime.utcnow().strftime("%Y%m%d")
        time_now = datetime.utcnow().strftime("%H%M")
        segments: list[str] = []

        # ISA – Interchange Control Header
        segments.append(self._line(
            "ISA", "00", " " * 10, "00", " " * 10,
            "ZZ", request.provider_npi.ljust(15),
            "ZZ", request.payer_id.ljust(15),
            today[2:],  # YYMMDD
            time_now,
            "^",  # repetition separator
            "00501",
            ctrl.ljust(9)[:9],
            "0",  # acknowledgment requested
            "P",  # production
            self._sub,
        ))

        # GS – Functional Group Header
        segments.append(self._line(
            "GS", "HS", request.provider_npi, request.payer_id,
            today, time_now, ctrl, "X", "005010X279A1",
        ))

        # ST – Transaction Set Header
        segments.append(self._line("ST", "270", ctrl[:4], "005010X279A1"))

        # BHT – Beginning of Hierarchical Transaction
        segments.append(self._line(
            "BHT", "0022", "13", ctrl, today, time_now,
        ))

        # -- HL 1 – Information Source (Payer) --------------------------------
        segments.append(self._line("HL", "1", "", "20", "1"))
        segments.append(self._line("NM1", "PR", "2", request.payer_name,
                                   "", "", "", "", "PI", request.payer_id))

        # -- HL 2 – Information Receiver (Provider) ---------------------------
        segments.append(self._line("HL", "2", "1", "21", "1"))
        segments.append(self._line("NM1", "1P", "1", request.provider_name,
                                   "", "", "", "", "XX", request.provider_npi))

        # -- HL 3 – Subscriber ------------------------------------------------
        segments.append(self._line("HL", "3", "2", "22", "0"))

        # TRN – Trace number
        segments.append(self._line("TRN", "1", ctrl, "9BUCKTEETH"))

        # NM1 – Subscriber name
        segments.append(self._line(
            "NM1", "IL", "1",
            request.subscriber_last_name,
            request.subscriber_first_name,
            "", "", "",
            "MI", request.subscriber_id,
        ))

        # DMG – Subscriber demographics
        segments.append(self._line(
            "DMG", "D8", request.subscriber_dob.strftime("%Y%m%d"),
        ))

        # DTP – Date of service
        segments.append(self._line(
            "DTP", "291", "D8", request.date_of_service.strftime("%Y%m%d"),
        ))

        # EQ – Eligibility/Benefit inquiry for each service type code
        for stc in request.service_type_codes:
            segments.append(self._line("EQ", stc))

        # SE – Transaction Set Trailer
        # Count includes ST and SE themselves
        segment_count = sum(
            1 for s in segments
            if not s.startswith("ISA") and not s.startswith("GS")
        ) + 1  # +1 for SE itself
        segments.append(self._line("SE", str(segment_count), ctrl[:4]))

        # GE – Functional Group Trailer
        segments.append(self._line("GE", "1", ctrl))

        # IEA – Interchange Control Trailer
        segments.append(self._line("IEA", "1", ctrl.ljust(9)[:9]))

        return "\n".join(segments)


# ---------------------------------------------------------------------------
# 271 – Eligibility Response
# ---------------------------------------------------------------------------
@dataclass
class EligibilityBenefit:
    """A single eligibility/benefit line parsed from an EB segment."""

    service_type: str = ""
    coverage_level: str = ""
    insurance_type: str = ""
    benefit_amount: Optional[float] = None
    benefit_percent: Optional[float] = None
    time_qualifier: str = ""
    time_period: str = ""
    quantity_qualifier: str = ""
    quantity: Optional[float] = None
    in_network: Optional[bool] = None
    authorization_required: bool = False
    description: str = ""


@dataclass
class EligibilityResponse:
    """Parsed X12 271 eligibility/benefit response."""

    subscriber_name: str = ""
    subscriber_id: str = ""
    payer_name: str = ""
    payer_id: str = ""
    plan_name: str = ""
    plan_number: str = ""
    coverage_status: str = ""  # "active" or "inactive"
    benefits: list[EligibilityBenefit] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Coverage-level codes (EB03)
_COVERAGE_LEVEL: dict[str, str] = {
    "IND": "Individual",
    "FAM": "Family",
    "CHD": "Children Only",
    "DEP": "Dependents Only",
    "ECH": "Employee and Children",
    "EMP": "Employee Only",
    "ESP": "Employee and Spouse",
}

# Time-period qualifiers (EB06)
_TIME_QUALIFIERS: dict[str, str] = {
    "6": "Hour",
    "7": "Day",
    "13": "24 Hours",
    "21": "Years",
    "22": "Service Year",
    "23": "Calendar Year",
    "24": "Year to Date",
    "25": "Contract",
    "26": "Episode",
    "27": "Visit",
    "28": "Outlier",
    "29": "Remaining",
    "30": "Exceeded",
    "31": "Not Exceeded",
    "32": "Lifetime",
    "33": "Lifetime Remaining",
    "34": "Month",
    "35": "Week",
    "36": "Admission",
}

# Information-type qualifiers (EB01)
_BENEFIT_INFO_CODES: dict[str, str] = {
    "1": "Active Coverage",
    "2": "Active - Full Risk Capitation",
    "3": "Active - Services Capitated",
    "4": "Active - Services Capitated to Primary Care Provider",
    "5": "Active - Pending Investigation",
    "6": "Inactive",
    "7": "Inactive - Pending Eligibility Update",
    "8": "Inactive - Pending Investigation",
    "A": "Co-Insurance",
    "B": "Co-Payment",
    "C": "Deductible",
    "D": "Benefit Description",
    "E": "Exclusions",
    "F": "Limitations",
    "G": "Out of Pocket (Stop Loss)",
    "H": "Unlimited",
    "I": "Non-Covered",
    "J": "Cost Containment",
    "K": "Reserve",
    "L": "Primary Care Provider",
    "M": "Pre-existing Condition",
    "MC": "Managed Care Coordinator",
    "N": "Services Restricted to Following Provider",
    "O": "Not Deemed a Medical Necessity",
    "P": "Benefit Disclaimer",
    "Q": "Second Surgical Opinion Required",
    "R": "Other or Additional Payor",
    "S": "Prior Year(s) History",
    "T": "Card(s) Reported Lost/Stolen",
    "U": "Contact Following Entity for Eligibility or Benefit Information",
    "V": "Cannot Process",
    "W": "Other Source of Data",
    "X": "Health Care Facility",
    "Y": "Spend Down",
    "CB": "Coverage Basis",
}


class X12_271_Parser:
    """Parses X12 271 (Eligibility/Benefit Response) transactions.

    Handles ``~`` or ``~\\n`` segment terminators and ``*`` element separators.
    Sub-element separators are detected from the ISA segment or default to ``:``.
    """

    def parse(self, raw_x12: str) -> EligibilityResponse:
        """Parse a raw X12 271 string into an :class:`EligibilityResponse`."""
        segments = self._split_segments(raw_x12)
        response = EligibilityResponse()

        sub_sep = self._detect_sub_element_sep(raw_x12)
        current_hl_level = ""
        current_entity = ""

        i = 0
        while i < len(segments):
            elements = segments[i]
            seg_id = elements[0] if elements else ""

            if seg_id == "HL":
                current_hl_level = self._safe_get(elements, 3)

            elif seg_id == "NM1":
                entity_code = self._safe_get(elements, 1)
                current_entity = entity_code

                if entity_code == "PR":
                    # Payer
                    response.payer_name = self._safe_get(elements, 3)
                    if self._safe_get(elements, 8) == "PI":
                        response.payer_id = self._safe_get(elements, 9)
                elif entity_code == "IL":
                    # Subscriber
                    last = self._safe_get(elements, 3)
                    first = self._safe_get(elements, 4)
                    middle = self._safe_get(elements, 5)
                    name_parts = [p for p in (first, middle, last) if p]
                    response.subscriber_name = " ".join(name_parts)
                    if self._safe_get(elements, 8) == "MI":
                        response.subscriber_id = self._safe_get(elements, 9)

            elif seg_id == "INS":
                ind_code = self._safe_get(elements, 1)
                if ind_code == "Y":
                    # Primary subscriber
                    pass

            elif seg_id == "REF":
                qualifier = self._safe_get(elements, 1)
                value = self._safe_get(elements, 2)
                if qualifier == "18":
                    response.plan_number = value

            elif seg_id == "EB":
                benefit = self._parse_eb_segment(elements, sub_sep)
                # Determine coverage status from EB01
                eb01 = self._safe_get(elements, 1)
                if eb01 in ("1", "2", "3", "4", "5"):
                    response.coverage_status = "active"
                elif eb01 in ("6", "7", "8"):
                    response.coverage_status = "inactive"

                # Look ahead for related segments (MSG, III, etc.)
                j = i + 1
                while j < len(segments):
                    next_elements = segments[j]
                    next_id = next_elements[0] if next_elements else ""
                    if next_id == "MSG":
                        msg_text = self._safe_get(next_elements, 1)
                        if msg_text:
                            benefit.description = (
                                (benefit.description + "; " + msg_text)
                                if benefit.description
                                else msg_text
                            )
                    elif next_id == "III":
                        # Additional info
                        pass
                    elif next_id == "DTP":
                        # Date info related to benefit
                        pass
                    elif next_id == "REF":
                        qualifier = self._safe_get(next_elements, 1)
                        value = self._safe_get(next_elements, 2)
                        if qualifier == "18":
                            response.plan_number = value
                        elif qualifier == "1L":
                            response.plan_name = value
                    elif next_id in ("EB", "HL", "NM1", "SE", "LS", "LE"):
                        break
                    j += 1

                response.benefits.append(benefit)

            elif seg_id == "AAA":
                # Error / rejection
                reject_code = self._safe_get(elements, 3)
                follow_up = self._safe_get(elements, 4)
                error_msg = f"Rejection: code={reject_code}"
                if follow_up:
                    error_msg += f", follow-up={follow_up}"
                response.errors.append(error_msg)

            i += 1

        # Derive plan name from benefit descriptions if not set
        if not response.plan_name:
            for benefit in response.benefits:
                eb01 = ""
                if benefit.description and benefit.service_type == "30":
                    response.plan_name = benefit.description
                    break

        return response

    # -- internal helpers ---------------------------------------------------

    def _split_segments(self, raw: str) -> list[list[str]]:
        """Split raw X12 into a list of segments, each a list of elements."""
        # Detect segment terminator
        if "~" in raw:
            term = "~"
        else:
            # Fallback: try newline-delimited
            term = "\n"

        # Detect element separator from ISA
        el_sep = "*"
        isa_match = re.search(r"ISA(.)", raw)
        if isa_match:
            el_sep = isa_match.group(1)

        # Split on terminator, strip whitespace
        raw_segments = raw.split(term)
        result: list[list[str]] = []
        for seg in raw_segments:
            seg = seg.strip()
            if not seg:
                continue
            elements = seg.split(el_sep)
            result.append(elements)
        return result

    def _detect_sub_element_sep(self, raw: str) -> str:
        """Detect the sub-element separator from the ISA segment."""
        # ISA16 is the component element separator – it's the character at
        # position 104 in a valid ISA (fixed-width 106 chars including ISA).
        isa_match = re.search(r"ISA.(.{100,106})", raw)
        if isa_match:
            isa_content = "ISA" + isa_match.group(0)[3:]
            if len(isa_content) >= 105:
                return isa_content[104]
        return ":"

    def _parse_eb_segment(
        self, elements: list[str], sub_sep: str
    ) -> EligibilityBenefit:
        """Parse an EB segment into an EligibilityBenefit."""
        benefit = EligibilityBenefit()

        eb01 = self._safe_get(elements, 1)
        eb02 = self._safe_get(elements, 2)
        eb03 = self._safe_get(elements, 3)
        eb04 = self._safe_get(elements, 4)
        eb05 = self._safe_get(elements, 5)
        eb06 = self._safe_get(elements, 6)
        eb07 = self._safe_get(elements, 7)
        eb08 = self._safe_get(elements, 8)
        eb09 = self._safe_get(elements, 9)
        eb10 = self._safe_get(elements, 10)
        eb11 = self._safe_get(elements, 11)
        eb12 = self._safe_get(elements, 12)
        eb13 = self._safe_get(elements, 13)

        # EB01 – Information type (used for coverage_status at caller level)
        benefit_code = _BENEFIT_INFO_CODES.get(eb01, eb01)

        # EB02 – Coverage level
        benefit.coverage_level = _COVERAGE_LEVEL.get(eb02, eb02)

        # EB03 – Service type code(s) – may contain sub-elements
        if eb03:
            stc_parts = eb03.split(sub_sep) if sub_sep in eb03 else [eb03]
            descriptions = []
            for code in stc_parts:
                desc = DENTAL_SERVICE_TYPE_CODES.get(code, code)
                descriptions.append(desc)
            benefit.service_type = ", ".join(descriptions)

        # EB04 – Insurance type code
        benefit.insurance_type = eb04

        # EB05 – Plan coverage description
        if eb05:
            benefit.description = eb05

        # EB06 – Time period qualifier
        if eb06:
            benefit.time_qualifier = _TIME_QUALIFIERS.get(eb06, eb06)
            benefit.time_period = benefit.time_qualifier

        # EB07 – Monetary amount
        if eb07:
            try:
                benefit.benefit_amount = float(eb07)
            except ValueError:
                pass

        # EB08 – Percent (as decimal, e.g., 0.80 = 80%)
        if eb08:
            try:
                benefit.benefit_percent = float(eb08)
            except ValueError:
                pass

        # EB09 – Quantity qualifier
        if eb09:
            benefit.quantity_qualifier = eb09

        # EB10 – Quantity
        if eb10:
            try:
                benefit.quantity = float(eb10)
            except ValueError:
                pass

        # EB11 – Authorization required
        if eb11:
            benefit.authorization_required = eb11 in ("Y", "y")

        # EB12 – In-network indicator
        if eb12:
            if eb12 == "Y":
                benefit.in_network = True
            elif eb12 == "N":
                benefit.in_network = False

        # If no description yet, derive from benefit info code
        if not benefit.description:
            benefit.description = benefit_code

        return benefit

    @staticmethod
    def _safe_get(elements: list[str], index: int, default: str = "") -> str:
        """Safely retrieve an element from a list."""
        if index < len(elements):
            return elements[index].strip()
        return default
