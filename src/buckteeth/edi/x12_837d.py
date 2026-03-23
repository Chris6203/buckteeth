"""X12 837D (Dental Claim) EDI transaction generator.

Generates HIPAA-compliant X12 837D transactions conforming to the ASC X12N
005010X224A2 implementation guide for dental claims. Supports primary and
secondary claims, predeterminations, and preauthorization requests.

Segment delimiters:
    * (asterisk)  - element separator
    : (colon)     - component element separator
    ~ (tilde)     - segment terminator
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buckteeth.models.claim import Claim, ClaimProcedure
    from buckteeth.models.coding import CodedProcedure
    from buckteeth.models.patient import Patient as PatientModel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ELEMENT_SEP = "*"
COMPONENT_SEP = ":"
SEGMENT_TERM = "~"

# Valid tooth numbers: universal (1-32) and primary (A-T)
UNIVERSAL_TEETH = {str(i) for i in range(1, 33)}
PRIMARY_TEETH = {chr(c) for c in range(ord("A"), ord("T") + 1)}
VALID_TOOTH_NUMBERS = UNIVERSAL_TEETH | PRIMARY_TEETH

# ADA surface codes
VALID_SURFACE_CODES = {"M", "O", "D", "B", "L", "I", "F"}

# Place of service codes (CMS-1500 subset relevant to dental)
PLACE_OF_SERVICE_CODES = {
    "11": "Office",
    "12": "Home",
    "21": "Inpatient Hospital",
    "22": "On Campus-Outpatient Hospital",
    "23": "Emergency Room - Hospital",
    "24": "Ambulatory Surgical Center",
    "31": "Skilled Nursing Facility",
    "32": "Nursing Facility",
    "33": "Custodial Care Facility",
    "49": "Independent Clinic",
    "50": "Federally Qualified Health Center",
    "71": "Public Health Clinic",
    "72": "Rural Health Clinic",
}

# Claim frequency codes (CLM05-3)
CLAIM_FREQUENCY_CODES = {
    "1": "Original",
    "7": "Replacement",
    "8": "Void",
}

# Transaction type codes for BHT06
TRANSACTION_TYPE_CODES = {
    "CH": "Chargeable",  # Standard claim
    "RP": "Reporting",
    "18": "Predetermination/Preauthorization",
}


class TransactionPurpose(str, Enum):
    """BHT02 - Transaction Set Purpose Code."""

    ORIGINAL = "00"  # Original claim
    RESUBMISSION = "18"  # Resubmission (predetermination/preauth request)


class ClaimFilingIndicator(str, Enum):
    """SBR09 - Claim Filing Indicator Code."""

    COMMERCIAL = "CI"
    MEDICAID = "MC"
    MEDICARE_PART_B = "MB"
    TRICARE = "CH"
    DENTAL_MAINTENANCE_ORG = "DN"
    PPO = "12"
    POS = "13"
    EPO = "14"
    INDEMNITY = "15"
    HMO_MEDICARE_RISK = "16"
    SELF_PAY = "09"
    OTHER = "ZZ"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ClaimSubmitter:
    """Interchange sender / submitter information (ISA/GS/NM1-41 loop)."""

    name: str
    ein: str
    contact_name: str
    contact_phone: str
    contact_email: str


@dataclass
class BillingProvider:
    """Billing provider (2010AA loop)."""

    npi: str
    tax_id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    taxonomy_code: str  # e.g. "1223G0001X" for general dentistry


@dataclass
class Subscriber:
    """Insurance subscriber / insured (2010BA loop)."""

    member_id: str
    group_number: str
    first_name: str
    last_name: str
    dob: date
    gender: str  # "M" or "F"
    address: str
    city: str
    state: str
    zip: str
    payer_name: str
    payer_id: str


@dataclass
class Patient:
    """Patient when different from subscriber (2010CA loop)."""

    first_name: str
    last_name: str
    dob: date
    gender: str  # "M" or "F"
    relationship_to_subscriber: str  # "18"=self, "01"=spouse, "19"=child, "20"=employee, "21"=unknown
    address: str
    city: str
    state: str
    zip: str


@dataclass
class DentalService:
    """Individual dental service line (2400 loop / SV3 segment)."""

    cdt_code: str  # e.g. "D2750"
    description: str
    fee: Decimal
    tooth_number: str | None = None
    tooth_surface: str | None = None  # concatenated surface codes e.g. "MOD"
    quadrant: str | None = None  # "UR", "UL", "LR", "LL" or "00"-"04"
    diagnosis_code_pointer: int | None = 1  # pointer into DentalClaim.diagnosis_codes
    date_of_service: date | None = None


@dataclass
class DentalClaim:
    """Complete dental claim for X12 837D generation."""

    claim_id: str
    subscriber: Subscriber
    billing_provider: BillingProvider
    submitter: ClaimSubmitter
    services: list[DentalService]
    diagnosis_codes: list[str] = field(default_factory=lambda: ["K02.9"])  # ICD-10
    patient: Patient | None = None  # None means subscriber is the patient
    prior_auth_number: str | None = None
    place_of_service: str = "11"  # office
    claim_frequency_code: str = "1"  # original
    total_charge: Decimal | None = None
    signature_on_file: bool = True
    assignment_of_benefits: bool = True
    transaction_purpose: TransactionPurpose = TransactionPurpose.ORIGINAL
    claim_filing_indicator: ClaimFilingIndicator = ClaimFilingIndicator.COMMERCIAL
    is_secondary: bool = False
    # For secondary claims - primary payer adjudication info
    primary_payer_name: str | None = None
    primary_payer_id: str | None = None
    primary_paid_amount: Decimal | None = None

    def __post_init__(self) -> None:
        if self.total_charge is None:
            self.total_charge = sum(s.fee for s in self.services)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_npi(npi: str) -> bool:
    """Validate NPI using the Luhn check-digit algorithm (ISO 176-1)."""
    if not re.fullmatch(r"\d{10}", npi):
        return False
    # NPI Luhn: prefix 80840 + NPI digits
    digits = [int(d) for d in "80840" + npi]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            doubled = d * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += d
    return total % 10 == 0


class X12_837D_Generator:
    """Generates X12 837D (dental claim) EDI transactions.

    Usage::

        gen = X12_837D_Generator(
            sender_id="SENDER123456789",
            receiver_id="RECEIVER12345678",
            sender_qualifier="ZZ",
            receiver_qualifier="ZZ",
        )
        edi_text = gen.generate(claim)
        errors = gen.validate(claim)
    """

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        sender_qualifier: str = "ZZ",
        receiver_qualifier: str = "ZZ",
        interchange_version: str = "00501",
        usage_indicator: str = "P",  # P=production, T=test
    ) -> None:
        self.sender_id = sender_id.ljust(15)
        self.receiver_id = receiver_id.ljust(15)
        self.sender_qualifier = sender_qualifier.ljust(2)
        self.receiver_qualifier = receiver_qualifier.ljust(2)
        self.interchange_version = interchange_version
        self.usage_indicator = usage_indicator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, claim: DentalClaim) -> list[str]:
        """Validate a claim for X12 837D compliance. Returns a list of errors."""
        errors: list[str] = []

        # Submitter
        if not claim.submitter.name:
            errors.append("Submitter name is required.")
        if not re.fullmatch(r"\d{9}", claim.submitter.ein.replace("-", "")):
            errors.append("Submitter EIN must be 9 digits.")
        if not claim.submitter.contact_phone:
            errors.append("Submitter contact phone is required.")

        # Billing provider
        bp = claim.billing_provider
        if not _validate_npi(bp.npi):
            errors.append(f"Billing provider NPI '{bp.npi}' is invalid.")
        if not re.fullmatch(r"\d{9}", bp.tax_id.replace("-", "")):
            errors.append("Billing provider Tax ID must be 9 digits.")
        if not bp.name:
            errors.append("Billing provider name is required.")
        if not bp.address or not bp.city or not bp.state or not bp.zip:
            errors.append("Billing provider address is incomplete.")
        if not re.fullmatch(r"\d{5}(\d{4})?", bp.zip.replace("-", "")):
            errors.append("Billing provider ZIP code is invalid.")
        if not bp.taxonomy_code:
            errors.append("Billing provider taxonomy code is required.")

        # Subscriber
        sub = claim.subscriber
        if not sub.member_id:
            errors.append("Subscriber member ID is required.")
        if not sub.first_name or not sub.last_name:
            errors.append("Subscriber name is required.")
        if sub.gender not in ("M", "F"):
            errors.append("Subscriber gender must be 'M' or 'F'.")
        if not sub.payer_id:
            errors.append("Payer ID is required.")

        # Patient (if different from subscriber)
        if claim.patient:
            pat = claim.patient
            if not pat.first_name or not pat.last_name:
                errors.append("Patient name is required.")
            if pat.gender not in ("M", "F"):
                errors.append("Patient gender must be 'M' or 'F'.")
            if pat.relationship_to_subscriber == "18":
                errors.append(
                    "Patient relationship '18' (self) should not have a "
                    "separate Patient record."
                )

        # Place of service
        if claim.place_of_service not in PLACE_OF_SERVICE_CODES:
            errors.append(
                f"Place of service '{claim.place_of_service}' is not a "
                f"recognized code."
            )

        # Claim frequency
        if claim.claim_frequency_code not in CLAIM_FREQUENCY_CODES:
            errors.append(
                f"Claim frequency code '{claim.claim_frequency_code}' is invalid."
            )

        # Diagnosis codes
        if not claim.diagnosis_codes:
            errors.append("At least one diagnosis code is required.")
        for dx in claim.diagnosis_codes:
            if not re.fullmatch(r"[A-Z]\d{2}(\.\d{1,4})?", dx):
                errors.append(f"Diagnosis code '{dx}' is not valid ICD-10 format.")

        # Services
        if not claim.services:
            errors.append("At least one service line is required.")
        for i, svc in enumerate(claim.services, 1):
            if not re.fullmatch(r"D\d{4}", svc.cdt_code):
                errors.append(f"Service {i}: CDT code '{svc.cdt_code}' format invalid (expected Dnnnn).")
            if svc.fee <= 0:
                errors.append(f"Service {i}: Fee must be greater than zero.")
            if svc.tooth_number and svc.tooth_number not in VALID_TOOTH_NUMBERS:
                errors.append(
                    f"Service {i}: Tooth number '{svc.tooth_number}' is not valid."
                )
            if svc.tooth_surface:
                for ch in svc.tooth_surface:
                    if ch not in VALID_SURFACE_CODES:
                        errors.append(
                            f"Service {i}: Surface code '{ch}' is not valid. "
                            f"Expected one of {VALID_SURFACE_CODES}."
                        )
            if svc.diagnosis_code_pointer is not None:
                if svc.diagnosis_code_pointer < 1 or svc.diagnosis_code_pointer > len(
                    claim.diagnosis_codes
                ):
                    errors.append(
                        f"Service {i}: Diagnosis code pointer "
                        f"{svc.diagnosis_code_pointer} out of range."
                    )

        # Total charge
        computed_total = sum(s.fee for s in claim.services)
        if claim.total_charge and claim.total_charge != computed_total:
            errors.append(
                f"Total charge {claim.total_charge} does not match sum of "
                f"service fees {computed_total}."
            )

        return errors

    def generate(self, claim: DentalClaim) -> str:
        """Generate a complete X12 837D transaction for a single claim."""
        now = datetime.now()
        icn = now.strftime("%y%m%d%H%M")  # 9-digit interchange control number
        gcn = "1"  # group control number

        segments: list[str] = []
        segments.extend(self._isa(now, icn))
        segments.extend(self._gs(now, gcn, claim.submitter))

        st_segments = self._transaction(claim, now, "0001")
        segments.extend(st_segments)

        segments.extend(self._ge(1, gcn))
        segments.extend(self._iea(1, icn))

        return SEGMENT_TERM.join(segments) + SEGMENT_TERM

    def generate_batch(self, claims: list[DentalClaim]) -> str:
        """Generate an X12 837D interchange containing multiple claims.

        All claims share one ISA/IEA envelope and one GS/GE functional group.
        Each claim gets its own ST/SE transaction set.
        """
        if not claims:
            raise ValueError("At least one claim is required.")

        now = datetime.now()
        icn = now.strftime("%y%m%d%H%M")
        gcn = "1"

        segments: list[str] = []
        segments.extend(self._isa(now, icn))
        segments.extend(self._gs(now, gcn, claims[0].submitter))

        for idx, claim in enumerate(claims, 1):
            st_num = str(idx).zfill(4)
            st_segments = self._transaction(claim, now, st_num)
            segments.extend(st_segments)

        segments.extend(self._ge(len(claims), gcn))
        segments.extend(self._iea(1, icn))

        return SEGMENT_TERM.join(segments) + SEGMENT_TERM

    # ------------------------------------------------------------------
    # Envelope segments
    # ------------------------------------------------------------------

    def _isa(self, now: datetime, icn: str) -> list[str]:
        """ISA - Interchange Control Header."""
        isa_date = now.strftime("%y%m%d")
        isa_time = now.strftime("%H%M")
        return [
            _seg(
                "ISA",
                "00",                            # ISA01 - Auth Info Qualifier
                " " * 10,                        # ISA02 - Auth Information
                "00",                            # ISA03 - Security Info Qualifier
                " " * 10,                        # ISA04 - Security Information
                self.sender_qualifier,           # ISA05 - Interchange Sender Qualifier
                self.sender_id,                  # ISA06 - Interchange Sender ID
                self.receiver_qualifier,         # ISA07 - Interchange Receiver Qualifier
                self.receiver_id,                # ISA08 - Interchange Receiver ID
                isa_date,                        # ISA09 - Interchange Date
                isa_time,                        # ISA10 - Interchange Time
                "^",                             # ISA11 - Repetition Separator
                self.interchange_version,        # ISA12 - Interchange Control Version
                icn.ljust(9)[:9],                # ISA13 - Interchange Control Number
                "0",                             # ISA14 - Ack Requested
                self.usage_indicator,            # ISA15 - Usage Indicator
                COMPONENT_SEP,                   # ISA16 - Component Separator
            )
        ]

    def _gs(self, now: datetime, gcn: str, submitter: ClaimSubmitter) -> list[str]:
        """GS - Functional Group Header."""
        gs_date = now.strftime("%Y%m%d")
        gs_time = now.strftime("%H%M")
        return [
            _seg(
                "GS",
                "HP",                            # GS01 - Functional Identifier (HP = Healthcare Claim)
                submitter.ein.replace("-", ""),   # GS02 - Application Sender's Code
                self.receiver_id.strip(),         # GS03 - Application Receiver's Code
                gs_date,                         # GS04 - Date
                gs_time,                         # GS05 - Time
                gcn,                             # GS06 - Group Control Number
                "X",                             # GS07 - Responsible Agency Code
                "005010X224A2",                  # GS08 - Version / Industry Code
            )
        ]

    def _ge(self, transaction_count: int, gcn: str) -> list[str]:
        """GE - Functional Group Trailer."""
        return [_seg("GE", str(transaction_count), gcn)]

    def _iea(self, group_count: int, icn: str) -> list[str]:
        """IEA - Interchange Control Trailer."""
        return [_seg("IEA", str(group_count), icn.ljust(9)[:9])]

    # ------------------------------------------------------------------
    # Transaction set (one per claim)
    # ------------------------------------------------------------------

    def _transaction(
        self, claim: DentalClaim, now: datetime, st_number: str
    ) -> list[str]:
        """Build ST through SE for a single dental claim."""
        segs: list[str] = []
        seg_count_start = len(segs)

        # ST - Transaction Set Header
        segs.append(_seg("ST", "837", st_number, "005010X224A2"))

        # BHT - Beginning of Hierarchical Transaction
        bht_purpose = claim.transaction_purpose.value
        bht_type = "18" if bht_purpose == "18" else "CH"
        bht_ref = claim.claim_id[:30]
        segs.append(
            _seg(
                "BHT",
                "0019",                          # BHT01 - Hierarchical Structure Code
                bht_purpose,                     # BHT02 - Transaction Set Purpose Code
                bht_ref,                         # BHT03 - Reference Identification
                now.strftime("%Y%m%d"),          # BHT04 - Date
                now.strftime("%H%M"),            # BHT05 - Time
                bht_type,                        # BHT06 - Transaction Type Code
            )
        )

        hl_counter = 0

        # --- HL Loop 1: Information Source (Submitter) ---
        hl_counter += 1
        hl_info_source = hl_counter
        segs.append(_seg("HL", str(hl_info_source), "", "20", "1"))

        # NM1 - Submitter Name (Loop 1000A)
        segs.append(
            _seg(
                "NM1",
                "41",                            # Entity Identifier: Submitter
                "2",                             # Entity Type: Non-Person
                claim.submitter.name[:60],       # Last Name / Org Name
                "",                              # First Name
                "",                              # Middle
                "",                              # Prefix
                "",                              # Suffix
                "46",                            # ID Code Qualifier: ETIN
                claim.submitter.ein.replace("-", ""),
            )
        )

        # PER - Submitter Contact
        per_elements = [
            "PER",
            "IC",                                # Contact Function Code
            claim.submitter.contact_name[:60],
            "TE",                                # Communication Qualifier: Telephone
            _phone(claim.submitter.contact_phone),
        ]
        if claim.submitter.contact_email:
            per_elements.extend([
                "EM",                            # Communication Qualifier: Email
                claim.submitter.contact_email[:80],
            ])
        segs.append(_seg(*per_elements))

        # NM1 - Receiver Name (Loop 1000B)
        segs.append(
            _seg(
                "NM1",
                "40",                            # Entity Identifier: Receiver
                "2",                             # Entity Type: Non-Person
                claim.subscriber.payer_name[:60],
                "",
                "",
                "",
                "",
                "46",                            # ID Code Qualifier: ETIN
                claim.subscriber.payer_id,
            )
        )

        # --- HL Loop 2: Billing/Pay-To Provider ---
        hl_counter += 1
        hl_billing = hl_counter
        segs.append(_seg("HL", str(hl_billing), str(hl_info_source), "22", "1"))

        # SBR or PRV at the billing provider level
        # PRV - Provider Specialty (2000A)
        segs.append(
            _seg(
                "PRV",
                "BI",                            # Provider Code: Billing
                "PXC",                           # Reference ID Qualifier: Taxonomy
                claim.billing_provider.taxonomy_code,
            )
        )

        # NM1 - Billing Provider Name (2010AA)
        segs.append(
            _seg(
                "NM1",
                "85",                            # Entity Identifier: Billing Provider
                "2",                             # Entity Type: Non-Person (organization)
                claim.billing_provider.name[:60],
                "",
                "",
                "",
                "",
                "XX",                            # ID Code Qualifier: NPI
                claim.billing_provider.npi,
            )
        )

        # N3 - Billing Provider Address
        segs.append(_seg("N3", claim.billing_provider.address[:55]))

        # N4 - Billing Provider City/State/Zip
        segs.append(
            _seg(
                "N4",
                claim.billing_provider.city[:30],
                claim.billing_provider.state[:2],
                claim.billing_provider.zip.replace("-", "")[:9],
            )
        )

        # REF - Billing Provider Tax ID
        tax_id = claim.billing_provider.tax_id.replace("-", "")
        segs.append(_seg("REF", "EI", tax_id))

        # --- HL Loop 3: Subscriber ---
        hl_counter += 1
        hl_subscriber = hl_counter
        has_patient = claim.patient is not None
        segs.append(
            _seg(
                "HL",
                str(hl_subscriber),
                str(hl_billing),
                "22",
                "1" if has_patient else "0",
            )
        )

        # SBR - Subscriber Information (2000B)
        payer_responsibility = "S" if claim.is_secondary else "P"
        relationship_code = (
            claim.patient.relationship_to_subscriber if claim.patient else "18"
        )
        segs.append(
            _seg(
                "SBR",
                payer_responsibility,            # SBR01 - Payer Responsibility
                relationship_code,               # SBR02 - Individual Relationship Code
                claim.subscriber.group_number,   # SBR03 - Group Number
                "",                              # SBR04 - Group Name
                "",                              # SBR05 - Insurance Type Code
                "",                              # SBR06
                "",                              # SBR07
                "",                              # SBR08
                claim.claim_filing_indicator.value,  # SBR09 - Claim Filing Indicator
            )
        )

        # NM1 - Subscriber Name (2010BA)
        segs.append(
            _seg(
                "NM1",
                "IL",                            # Entity Identifier: Insured/Subscriber
                "1",                             # Entity Type: Person
                claim.subscriber.last_name[:60],
                claim.subscriber.first_name[:35],
                "",                              # Middle
                "",                              # Prefix
                "",                              # Suffix
                "MI",                            # ID Code Qualifier: Member ID
                claim.subscriber.member_id,
            )
        )

        # N3 - Subscriber Address
        segs.append(_seg("N3", claim.subscriber.address[:55]))

        # N4 - Subscriber City/State/Zip
        segs.append(
            _seg(
                "N4",
                claim.subscriber.city[:30],
                claim.subscriber.state[:2],
                claim.subscriber.zip.replace("-", "")[:9],
            )
        )

        # DMG - Subscriber Demographics
        segs.append(
            _seg(
                "DMG",
                "D8",                            # Date Format: CCYYMMDD
                _format_date(claim.subscriber.dob),
                claim.subscriber.gender,
            )
        )

        # NM1 - Payer Name (2010BB)
        segs.append(
            _seg(
                "NM1",
                "PR",                            # Entity Identifier: Payer
                "2",                             # Entity Type: Non-Person
                claim.subscriber.payer_name[:60],
                "",
                "",
                "",
                "",
                "PI",                            # ID Code Qualifier: Payer ID
                claim.subscriber.payer_id,
            )
        )

        # --- HL Loop 4: Patient (if different from subscriber) ---
        if has_patient:
            hl_counter += 1
            hl_patient = hl_counter
            segs.append(
                _seg("HL", str(hl_patient), str(hl_subscriber), "23", "0")
            )

            # PAT - Patient Information (2000C)
            segs.append(
                _seg("PAT", claim.patient.relationship_to_subscriber)
            )

            # NM1 - Patient Name (2010CA)
            segs.append(
                _seg(
                    "NM1",
                    "QC",                        # Entity Identifier: Patient
                    "1",                         # Entity Type: Person
                    claim.patient.last_name[:60],
                    claim.patient.first_name[:35],
                )
            )

            # N3 - Patient Address
            segs.append(_seg("N3", claim.patient.address[:55]))

            # N4 - Patient City/State/Zip
            segs.append(
                _seg(
                    "N4",
                    claim.patient.city[:30],
                    claim.patient.state[:2],
                    claim.patient.zip.replace("-", "")[:9],
                )
            )

            # DMG - Patient Demographics
            segs.append(
                _seg(
                    "DMG",
                    "D8",
                    _format_date(claim.patient.dob),
                    claim.patient.gender,
                )
            )

        # --- Claim Level (2300 Loop) ---

        # CLM - Claim Information
        total = _format_amount(claim.total_charge)
        # CLM05: Place of service : facility code qualifier : claim frequency code
        clm05 = f"{claim.place_of_service}{COMPONENT_SEP}B{COMPONENT_SEP}{claim.claim_frequency_code}"
        signature = "Y" if claim.signature_on_file else "N"
        assignment = "A" if claim.assignment_of_benefits else "B"
        benefits_code = "Y" if claim.assignment_of_benefits else "N"
        segs.append(
            _seg(
                "CLM",
                claim.claim_id[:38],             # CLM01 - Patient Control Number
                total,                           # CLM02 - Total Claim Charge
                "",                              # CLM03
                "",                              # CLM04
                clm05,                           # CLM05 - Health Care Service Location
                "",                              # CLM06
                "A",                             # CLM07 - Provider Accept Assignment (A=assigned)
                benefits_code,                   # CLM08 - Benefits Assignment Certification
                signature,                       # CLM09 - Release of Information Code
            )
        )

        # DTP - Date of Service (claim-level)
        # Use the first service date or today
        service_dates = [
            s.date_of_service for s in claim.services if s.date_of_service
        ]
        claim_date = min(service_dates) if service_dates else date.today()
        segs.append(_seg("DTP", "472", "D8", _format_date(claim_date)))

        # REF - Prior Authorization Number (if present)
        if claim.prior_auth_number:
            segs.append(_seg("REF", "G1", claim.prior_auth_number))

        # HI - Diagnosis Codes (2300)
        if claim.diagnosis_codes:
            # First diagnosis as principal
            hi_components = []
            for i, dx in enumerate(claim.diagnosis_codes):
                qualifier = "ABK" if i == 0 else "ABF"
                hi_components.append(f"{qualifier}{COMPONENT_SEP}{dx}")
            segs.append(_seg("HI", *hi_components))

        # DN1 - Orthodontic Total Months of Treatment / DN2 - Tooth Status
        # These are situational; only emit when appropriate based on services

        # --- 2400 Loop: Service Lines ---
        for line_num, svc in enumerate(claim.services, 1):
            segs.extend(self._service_line(svc, line_num, claim))

        # SE - Transaction Set Trailer
        segment_count = len(segs) - seg_count_start + 1  # +1 for SE itself
        segs.append(_seg("SE", str(segment_count), st_number))

        return segs

    # ------------------------------------------------------------------
    # Service line (2400 loop)
    # ------------------------------------------------------------------

    def _service_line(
        self,
        svc: DentalService,
        line_num: int,
        claim: DentalClaim,
    ) -> list[str]:
        """Build segments for a single dental service line."""
        segs: list[str] = []

        # LX - Service Line Number
        segs.append(_seg("LX", str(line_num)))

        # SV3 - Dental Service
        # SV301: composite (AD:CDT code)
        sv3_01 = f"AD{COMPONENT_SEP}{svc.cdt_code}"
        sv3_02 = _format_amount(svc.fee)
        sv3_03 = claim.place_of_service  # Facility Code Value
        sv3_04 = ""  # Oral Cavity Designation Code (used for quadrant/arch)

        # SV304 - Oral Cavity Designation
        if svc.quadrant:
            sv3_04 = _map_quadrant(svc.quadrant)

        # SV305 - Prosthesis, Crown, or Inlay Code (situational)
        sv3_05 = ""

        # SV306 - Procedure Count
        sv3_06 = "1"

        # SV307 - Description (situational, not typically sent electronically)
        sv3_07 = ""

        # Build SV3 with diagnosis pointer
        sv3_elements = ["SV3", sv3_01, sv3_02, sv3_03, sv3_04, sv3_05, sv3_06]
        # SV311 - Diagnosis Code Pointer (if present)
        if svc.diagnosis_code_pointer:
            # Pad elements 7-10 then add pointer at position 11
            while len(sv3_elements) < 11:
                sv3_elements.append("")
            sv3_elements.append(str(svc.diagnosis_code_pointer))

        segs.append(_seg(*sv3_elements))

        # TOO - Tooth Information
        if svc.tooth_number:
            too_elements = [
                "TOO",
                "JP",                            # Code List Qualifier (JP = Universal Tooth Designation)
                svc.tooth_number,
            ]
            # TOO03 - Tooth Surface (composite, each surface is a component)
            if svc.tooth_surface:
                surface_composite = COMPONENT_SEP.join(list(svc.tooth_surface))
                too_elements.append(surface_composite)
            segs.append(_seg(*too_elements))

        # DTP - Date of Service (service line level)
        svc_date = svc.date_of_service or date.today()
        segs.append(_seg("DTP", "472", "D8", _format_date(svc_date)))

        return segs


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _seg(*elements: str) -> str:
    """Build a segment string from elements, stripping trailing empty elements."""
    # Remove trailing empty strings to produce cleaner output
    el_list = list(elements)
    while el_list and el_list[-1] == "":
        el_list.pop()
    return ELEMENT_SEP.join(el_list)


def _format_date(d: date) -> str:
    """Format a date as CCYYMMDD."""
    return d.strftime("%Y%m%d")


def _format_amount(amount: Decimal | None) -> str:
    """Format a monetary amount to 2 decimal places without trailing zeros issues."""
    if amount is None:
        return "0"
    quantized = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return str(quantized)


def _phone(raw: str) -> str:
    """Normalize phone to digits only."""
    return re.sub(r"\D", "", raw)[:10]


def _map_quadrant(quadrant: str) -> str:
    """Map quadrant description to ADA oral cavity designation code.

    ADA Oral Cavity Designation Codes:
        10 = Upper right (UR)
        20 = Upper left (UL)
        30 = Lower left (LL)
        40 = Lower right (LR)
        00 = Entire oral cavity
        01 = Maxillary arch
        02 = Mandibular arch
    """
    mapping = {
        "UR": "10",
        "UL": "20",
        "LL": "30",
        "LR": "40",
        "10": "10",
        "20": "20",
        "30": "30",
        "40": "40",
        "00": "00",
        "01": "01",
        "02": "02",
    }
    return mapping.get(quadrant.upper(), "")


# ---------------------------------------------------------------------------
# SQLAlchemy model conversion helper
# ---------------------------------------------------------------------------


def to_claim_data(
    claim_model: Claim,
    patient_model: PatientModel,
    coded_procedures: list[CodedProcedure],
    billing_provider: BillingProvider,
    submitter: ClaimSubmitter,
    *,
    is_secondary: bool = False,
    prior_auth_number: str | None = None,
    claim_filing_indicator: ClaimFilingIndicator = ClaimFilingIndicator.COMMERCIAL,
) -> DentalClaim:
    """Convert SQLAlchemy models to X12 837D dataclasses.

    This bridges the application's ORM models (Claim, Patient, CodedProcedure)
    to the EDI generator's input dataclasses.

    Args:
        claim_model: The Claim ORM instance.
        patient_model: The Patient ORM instance.
        coded_procedures: List of CodedProcedure ORM instances for this claim.
        billing_provider: Pre-built BillingProvider (from practice configuration).
        submitter: Pre-built ClaimSubmitter (from practice configuration).
        is_secondary: Whether this is a secondary payer claim.
        prior_auth_number: Optional prior authorization number override.
            Falls back to claim_model.preauth_number.
        claim_filing_indicator: Payer type code. Defaults to commercial.

    Returns:
        A fully populated DentalClaim ready for X12 generation.
    """
    # Build subscriber from claim + patient models
    subscriber = Subscriber(
        member_id=claim_model.primary_subscriber_id if not is_secondary
        else (claim_model.secondary_subscriber_id or claim_model.primary_subscriber_id),
        group_number=claim_model.primary_group_number if not is_secondary
        else (claim_model.secondary_group_number or claim_model.primary_group_number),
        first_name=patient_model.first_name,
        last_name=patient_model.last_name,
        dob=_parse_date_str(patient_model.date_of_birth),
        gender=patient_model.gender[0].upper() if patient_model.gender else "M",
        address="",   # Address not stored on Patient model; must be supplemented
        city="",
        state="",
        zip="",
        payer_name=claim_model.primary_payer_name if not is_secondary
        else (claim_model.secondary_payer_name or claim_model.primary_payer_name),
        payer_id=claim_model.primary_payer_id if not is_secondary
        else (claim_model.secondary_payer_id or claim_model.primary_payer_id),
    )

    # Build service lines from coded procedures
    services: list[DentalService] = []
    diagnosis_codes: list[str] = []
    seen_dx: set[str] = set()

    for cp in coded_procedures:
        # Collect ICD-10 codes
        dx_pointer = 1
        if cp.icd10_codes and isinstance(cp.icd10_codes, list):
            for dx in cp.icd10_codes:
                if dx not in seen_dx:
                    seen_dx.add(dx)
                    diagnosis_codes.append(dx)
                dx_pointer = diagnosis_codes.index(dx) + 1

        # Find matching claim procedure for fee
        fee = Decimal("0")
        for cp_line in getattr(claim_model, "procedures", []):
            if str(cp_line.coded_procedure_id) == str(cp.id):
                fee = Decimal(str(cp_line.fee_submitted or 0))
                break

        svc_date = _parse_date_str(claim_model.date_of_service)

        services.append(
            DentalService(
                cdt_code=cp.cdt_code,
                description=cp.cdt_description,
                fee=fee,
                tooth_number=cp.tooth_number,
                tooth_surface=cp.surfaces,
                quadrant=cp.quadrant,
                diagnosis_code_pointer=dx_pointer,
                date_of_service=svc_date,
            )
        )

    # Fallback diagnosis
    if not diagnosis_codes:
        diagnosis_codes = ["K02.9"]  # Dental caries, unspecified

    auth_number = prior_auth_number or claim_model.preauth_number

    return DentalClaim(
        claim_id=str(claim_model.id),
        subscriber=subscriber,
        billing_provider=billing_provider,
        submitter=submitter,
        services=services,
        diagnosis_codes=diagnosis_codes,
        prior_auth_number=auth_number,
        place_of_service="11",
        claim_frequency_code="1",
        signature_on_file=True,
        assignment_of_benefits=True,
        claim_filing_indicator=claim_filing_indicator,
        is_secondary=is_secondary,
    )


def _parse_date_str(date_str: str | None) -> date:
    """Parse a date string in common formats to a date object."""
    if not date_str:
        return date.today()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return date.today()
