"""X12 835 Electronic Remittance Advice (ERA) parser for dental claims.

Parses X12 835 (Health Care Claim Payment/Advice) transactions into structured
Python dataclasses with full support for dental-specific adjustment reason codes,
remark codes, and CDT procedure codes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Claim Adjustment Reason Codes (CARC) – dental-specific subset
# ---------------------------------------------------------------------------
CARC_CODES: dict[str, str] = {
    # Source: X12.org official CARC code list (verified 2026-03-23)
    "1": "Deductible amount",
    "2": "Coinsurance amount",
    "3": "Co-payment amount",
    "4": "Procedure code inconsistent with modifier used",
    "5": "Procedure code inconsistent with place of service",
    "6": "Procedure/revenue code inconsistent with patient age",
    "9": "Diagnosis inconsistent with patient gender",
    "11": "Diagnosis inconsistent with procedure",
    "16": "Claim/service lacks information or has submission/billing errors",
    "18": "Exact duplicate claim/service",
    "22": "This care may be covered by another payer per coordination of benefits",
    "23": "Impact of prior payer adjudication including payments and/or adjustments",
    "24": "Charges are covered under a capitation agreement/managed care plan",
    "27": "Expenses incurred after coverage terminated",
    "29": "The time limit for filing has expired",
    "31": "Patient cannot be identified as our insured",
    "35": "Lifetime benefit maximum has been reached",
    "39": "Services denied at the time authorization/pre-certification was requested",
    "45": "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement",
    "49": "Non-covered service because it is a routine/preventive exam",
    "50": "Non-covered services deemed not medically necessary by payer",
    "55": "Procedure/treatment/drug is deemed experimental/investigational",
    "58": "Treatment was deemed by the payer to have been rendered in an inappropriate setting",
    "59": "Processed based on multiple or concurrent procedure rules",
    "89": "Services not provided by network/primary care providers",
    "96": "Non-covered charge(s)",
    "97": "Benefit for this service included in payment for another service already adjudicated",
    "109": "Claim/service not covered by this payer/contractor",
    "119": "Benefit maximum for this time period or occurrence has been reached",
    "128": "Newborn's services are covered in the mother's allowance",
    "129": "Prior processing information",
    "136": "Failure to follow prior authorization guidelines",
    "146": "Diagnosis was invalid for the date(s) of service reported",
    "151": "Payment adjusted because the payer deems the information submitted does not support this many services",
    "167": "This (these) diagnosis(es) is (are) not covered",
    "170": "Payment denied when performed/billed by this provider type",
    "181": "Procedure code was invalid on the date of service",
    "197": "Precertification/authorization/notification/pre-treatment absent",
    "198": "Precertification/notification/authorization exceeded",
    "204": "This service/equipment/drug is not covered under the patient's current benefit plan",
    "219": "Based on subrogation of a third party settlement",
    "226": "Information requested from the billing/rendering provider was not provided or was insufficient",
    "234": "This procedure is not paid separately",
    "235": "Sales tax",
    "242": "Services not provided by network/primary care providers",
    "253": "Sequestration - reduction in federal payment",
    # Dental-specific CARC codes
    "N362": "Missing/incomplete/invalid tooth number",
    "N382": "Missing/incomplete/invalid tooth surface",
    "N432": "Alert: eligibility response (271) was not received",
    "N523": "Missing pre-authorization for this procedure",
}


# ---------------------------------------------------------------------------
# Remittance Advice Remark Codes (RARC) – top 20 dental codes
# ---------------------------------------------------------------------------
RARC_CODES: dict[str, str] = {
    "M1": "X-ray not taken within the past 12 months or near enough to the start of treatment",
    "M15": "Separately billed services/tests have been bundled as they are considered components of the same procedure",
    "M20": "Missing/incomplete/invalid HCPCS",
    "M27": "Missing/incomplete/invalid entitlement number or SSN",
    "M49": "Missing/incomplete/invalid value code(s) or amount(s)",
    "M51": "Missing/incomplete/invalid procedure code(s)",
    "M76": "Missing/incomplete/invalid diagnosis or condition or treatment code(s)",
    "M80": "Not covered when performed during the same session/date as a previously processed service for the patient",
    "N4": "Missing/incomplete/invalid prior insurance carrier EOB",
    "N19": "Procedure code incidental to primary procedure",
    "N20": "Service not payable with other service rendered on the same date",
    "N30": "Patient ineligible for this service",
    "N115": "This decision was based on a National Coverage Determination (NCD)",
    "N130": "Consult plan benefit documents/guidelines for specifics on limitations or non-covered services",
    "N341": "Claim does not qualify for payment under the Global Surgery rules",
    "N362": "Missing/incomplete/invalid tooth number",
    "N382": "Missing/incomplete/invalid tooth surface",
    "N386": "This decision was based on a Local Coverage Determination (LCD)",
    "N425": "Missing/incomplete/invalid tooth surface information",
    "N432": "Alert: A 271 response was not received",
}


# ---------------------------------------------------------------------------
# Group codes for claim adjustments
# ---------------------------------------------------------------------------
GROUP_CODES: dict[str, str] = {
    "CO": "Contractual Obligation",
    "OA": "Other Adjustment",
    "PI": "Payer Initiated Reduction",
    "PR": "Patient Responsibility",
}


# ---------------------------------------------------------------------------
# Claim status codes
# ---------------------------------------------------------------------------
CLAIM_STATUS_CODES: dict[str, str] = {
    "1": "processed_primary",
    "2": "processed_secondary",
    "3": "processed_tertiary",
    "4": "denied",
    "19": "processed_primary_forwarded",
    "20": "processed_secondary_forwarded",
    "22": "reversal",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ClaimAdjustment:
    """A single adjustment within a CAS segment."""

    group_code: str  # CO, OA, PI, PR
    reason_code: str
    amount: float
    quantity: Optional[float] = None

    @property
    def group_description(self) -> str:
        return GROUP_CODES.get(self.group_code, self.group_code)

    @property
    def reason_description(self) -> str:
        return CARC_CODES.get(self.reason_code, f"Unknown ({self.reason_code})")


@dataclass
class ServicePayment:
    """Payment detail for a single service line (SVC segment)."""

    cdt_code: str
    charge_amount: float
    paid_amount: float
    adjustments: list[ClaimAdjustment] = field(default_factory=list)
    allowed_amount: Optional[float] = None
    patient_responsibility: float = 0.0
    remark_codes: list[str] = field(default_factory=list)


@dataclass
class ClaimPayment:
    """Payment detail for a single claim (CLP segment)."""

    claim_id: str
    patient_name: str
    payer_name: str
    total_charge: float
    total_paid: float
    patient_responsibility: float
    claim_status: str  # e.g. "processed_primary", "denied"
    service_payments: list[ServicePayment] = field(default_factory=list)
    check_number: str = ""
    check_date: str = ""


@dataclass
class RemittanceAdvice:
    """Top-level 835 remittance advice."""

    payer_name: str = ""
    payer_id: str = ""
    payee_name: str = ""
    payment_method: str = ""  # CHK or ACH
    total_paid: float = 0.0
    claims: list[ClaimPayment] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class X12_835_Parser:
    """Parses X12 835 (Electronic Remittance Advice) transactions.

    Supports standard X12 delimiters detected from the ISA segment.
    """

    def parse(self, raw_x12: str) -> RemittanceAdvice:
        """Parse a raw X12 835 string into a :class:`RemittanceAdvice`."""
        el_sep, sub_sep, seg_term = self._detect_delimiters(raw_x12)
        segments = self._split_segments(raw_x12, el_sep, seg_term)
        ra = RemittanceAdvice()

        current_claim: Optional[ClaimPayment] = None
        current_service: Optional[ServicePayment] = None
        check_number = ""
        check_date = ""
        payer_name = ""

        i = 0
        while i < len(segments):
            elements = segments[i]
            seg_id = elements[0] if elements else ""

            # ----- N1 – Entity identification --------------------------------
            if seg_id == "N1":
                entity_id = self._safe_get(elements, 1)
                name = self._safe_get(elements, 2)
                id_qualifier = self._safe_get(elements, 3)
                id_value = self._safe_get(elements, 4)

                if entity_id == "PR":
                    ra.payer_name = name
                    ra.payer_id = id_value
                    payer_name = name
                elif entity_id == "PE":
                    ra.payee_name = name

            # ----- BPR – Financial information -------------------------------
            elif seg_id == "BPR":
                transaction_type = self._safe_get(elements, 1)
                amount = self._safe_get(elements, 2)
                payment_method = self._safe_get(elements, 4)

                if amount:
                    try:
                        ra.total_paid = float(amount)
                    except ValueError:
                        pass

                if payment_method in ("CHK", "ACH"):
                    ra.payment_method = payment_method
                elif payment_method == "NON":
                    ra.payment_method = "NON"
                else:
                    ra.payment_method = payment_method

            # ----- TRN – Reassociation trace ---------------------------------
            elif seg_id == "TRN":
                trace_number = self._safe_get(elements, 2)
                if not check_number:
                    check_number = trace_number

            # ----- DTM – Date/time reference ---------------------------------
            elif seg_id == "DTM":
                qualifier = self._safe_get(elements, 1)
                date_val = self._safe_get(elements, 2)
                if qualifier == "405":
                    # Production date (check date)
                    check_date = date_val

            # ----- CLP – Claim payment information ---------------------------
            elif seg_id == "CLP":
                # Finalize previous service into previous claim
                if current_service and current_claim:
                    current_claim.service_payments.append(current_service)
                    current_service = None

                # Finalize previous claim
                if current_claim:
                    ra.claims.append(current_claim)

                claim_id = self._safe_get(elements, 1)
                status_code = self._safe_get(elements, 2)
                total_charge = self._to_float(self._safe_get(elements, 3))
                total_paid = self._to_float(self._safe_get(elements, 4))
                patient_resp = self._to_float(self._safe_get(elements, 5))

                claim_status = CLAIM_STATUS_CODES.get(status_code, status_code)

                current_claim = ClaimPayment(
                    claim_id=claim_id,
                    patient_name="",
                    payer_name=payer_name,
                    total_charge=total_charge,
                    total_paid=total_paid,
                    patient_responsibility=patient_resp,
                    claim_status=claim_status,
                    check_number=check_number,
                    check_date=check_date,
                )

            # ----- NM1 within claim context (patient name) -------------------
            elif seg_id == "NM1" and current_claim is not None:
                entity_code = self._safe_get(elements, 1)
                if entity_code == "QC":
                    # Patient
                    last = self._safe_get(elements, 3)
                    first = self._safe_get(elements, 4)
                    middle = self._safe_get(elements, 5)
                    name_parts = [p for p in (first, middle, last) if p]
                    current_claim.patient_name = " ".join(name_parts)

            # ----- CAS – Claim adjustment (claim-level, before SVC) ----------
            elif seg_id == "CAS" and current_claim is not None and current_service is None:
                adjustments = self._parse_cas(elements)
                # Claim-level adjustments go to the claim; we can store them
                # as service-level if there are no service lines, or accumulate
                # patient responsibility.
                for adj in adjustments:
                    if adj.group_code == "PR":
                        current_claim.patient_responsibility += adj.amount

            # ----- SVC – Service payment information -------------------------
            elif seg_id == "SVC":
                # Finalize previous service
                if current_service and current_claim:
                    current_claim.service_payments.append(current_service)

                composite = self._safe_get(elements, 1)
                # SVC01 is a composite: qualifier:code or qualifier*code
                cdt_code = self._extract_procedure_code(composite, sub_sep)
                charge = self._to_float(self._safe_get(elements, 2))
                paid = self._to_float(self._safe_get(elements, 3))

                # SVC05 can be bundled/original units
                allowed = None
                # SVC04 = NUBC revenue code (not always present)
                # SVC05 = original units of service
                # SVC06 = bundled line number

                current_service = ServicePayment(
                    cdt_code=cdt_code,
                    charge_amount=charge,
                    paid_amount=paid,
                )

            # ----- CAS within service context --------------------------------
            elif seg_id == "CAS" and current_service is not None:
                adjustments = self._parse_cas(elements)
                current_service.adjustments.extend(adjustments)
                for adj in adjustments:
                    if adj.group_code == "PR":
                        current_service.patient_responsibility += adj.amount

            # ----- AMT – Monetary amount within service ----------------------
            elif seg_id == "AMT" and current_service is not None:
                qualifier = self._safe_get(elements, 1)
                amount = self._to_float(self._safe_get(elements, 2))
                if qualifier == "B6":
                    # Allowed amount
                    current_service.allowed_amount = amount

            # ----- LQ – Remark codes ----------------------------------------
            elif seg_id == "LQ" and current_service is not None:
                qualifier = self._safe_get(elements, 1)
                code = self._safe_get(elements, 2)
                if qualifier in ("HE", "RX"):
                    current_service.remark_codes.append(code)

            # ----- PLB – Provider-level balance (end of remittance) ----------
            elif seg_id == "PLB":
                pass  # Provider-level adjustments – not modeled here

            i += 1

        # Finalize last service and claim
        if current_service and current_claim:
            current_claim.service_payments.append(current_service)
        if current_claim:
            ra.claims.append(current_claim)

        return ra

    # -- delimiter detection ------------------------------------------------

    @staticmethod
    def _detect_delimiters(raw: str) -> tuple[str, str, str]:
        """Detect element separator, sub-element separator, and segment terminator.

        The ISA segment is fixed-length (106 characters):
        - ISA[3] = element separator (usually ``*``)
        - ISA[104] = sub-element separator (usually ``:`` or ``^``)
        - ISA[105] = segment terminator (usually ``~``)
        """
        el_sep = "*"
        sub_sep = ":"
        seg_term = "~"

        isa_pos = raw.find("ISA")
        if isa_pos >= 0:
            isa_block = raw[isa_pos:]
            if len(isa_block) >= 4:
                el_sep = isa_block[3]
            if len(isa_block) >= 106:
                sub_sep = isa_block[104]
                seg_term = isa_block[105]
            elif "~" in isa_block:
                seg_term = "~"

        return el_sep, sub_sep, seg_term

    # -- segment splitting --------------------------------------------------

    @staticmethod
    def _split_segments(
        raw: str, el_sep: str, seg_term: str
    ) -> list[list[str]]:
        """Split the raw X12 into a list of segments (each a list of elements)."""
        raw_segments = raw.split(seg_term)
        result: list[list[str]] = []
        for seg in raw_segments:
            seg = seg.strip()
            if not seg:
                continue
            elements = seg.split(el_sep)
            result.append(elements)
        return result

    # -- CAS parsing --------------------------------------------------------

    def _parse_cas(self, elements: list[str]) -> list[ClaimAdjustment]:
        """Parse a CAS (Claim Adjustment) segment.

        CAS segments can contain up to 6 adjustment groups of 3 elements each:
        CAS*group*reason1*amount1*quantity1*reason2*amount2*quantity2*...
        """
        group_code = self._safe_get(elements, 1)
        adjustments: list[ClaimAdjustment] = []

        idx = 2
        while idx < len(elements):
            reason = self._safe_get(elements, idx)
            if not reason:
                break
            amount = self._to_float(self._safe_get(elements, idx + 1))
            qty_str = self._safe_get(elements, idx + 2)
            quantity = self._to_float(qty_str) if qty_str else None

            adjustments.append(ClaimAdjustment(
                group_code=group_code,
                reason_code=reason,
                amount=amount,
                quantity=quantity,
            ))
            idx += 3

        return adjustments

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_procedure_code(composite: str, sub_sep: str) -> str:
        """Extract the procedure code from an SVC01 composite element.

        SVC01 is typically ``HC:D2750`` or ``AD:D0120`` where the qualifier
        indicates the code set and the second component is the procedure code.
        """
        parts = composite.split(sub_sep) if sub_sep in composite else [composite]
        if len(parts) >= 2:
            return parts[1]
        return composite

    @staticmethod
    def _safe_get(elements: list[str], index: int, default: str = "") -> str:
        if index < len(elements):
            return elements[index].strip()
        return default

    @staticmethod
    def _to_float(value: str) -> float:
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0
