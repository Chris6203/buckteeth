"""
Claim.MD Clearinghouse Adapter

Claim.MD provides a REST API for submitting dental/medical claims,
checking eligibility, and retrieving claim status/ERAs.

API Docs: https://www.claim.md/developers/
Sandbox: https://svc.claim.md/services/

Authentication: Account ID + Auth Key (HTTP headers)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import httpx

from buckteeth.submission.adapters import (
    ClearinghouseAdapter,
    ClaimStatus,
    EligibilityResult,
    SubmissionResult,
)

logger = logging.getLogger(__name__)


class ClaimMDEnvironment(Enum):
    SANDBOX = "https://svc.claim.md/services"
    PRODUCTION = "https://svc.claim.md/services"


@dataclass
class ClaimMDConfig:
    """Configuration for Claim.MD API access."""

    account_id: str
    auth_key: str
    environment: ClaimMDEnvironment = ClaimMDEnvironment.SANDBOX
    timeout: float = 30.0

    @property
    def base_url(self) -> str:
        return self.environment.value


@dataclass
class ClaimMDResponse:
    """Raw response from Claim.MD API."""

    success: bool
    status: str
    message: str
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class ClaimMDAdapter(ClearinghouseAdapter):
    """
    Claim.MD clearinghouse adapter.

    Supports:
    - Professional (CMS-1500) and Dental (ADA) claim submission
    - Real-time eligibility verification (270/271)
    - Claim status inquiry
    - ERA (835) retrieval
    - Claim.MD accepts both X12 EDI and their JSON format

    Enrollment:
    - Register at https://www.claim.md
    - Get Account ID and Auth Key from dashboard
    - Sandbox available for testing without real payer connections
    """

    def __init__(self, config: ClaimMDConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _request(
        self, method: str, endpoint: str, data: dict | None = None,
    ) -> ClaimMDResponse:
        """Make authenticated request to Claim.MD API."""
        client = await self._get_client()

        payload = {
            "AccountID": self.config.account_id,
            "AuthKey": self.config.auth_key,
            **(data or {}),
        }

        try:
            if method == "GET":
                resp = await client.get(endpoint, params=payload)
            else:
                resp = await client.post(endpoint, json=payload)

            resp.raise_for_status()
            body = resp.json()

            return ClaimMDResponse(
                success=body.get("Status", "") in ("OK", "Accepted", "Success"),
                status=body.get("Status", "Unknown"),
                message=body.get("Message", ""),
                data=body,
                errors=body.get("Errors", []),
            )
        except httpx.HTTPStatusError as e:
            logger.error("Claim.MD HTTP error: %s", e)
            return ClaimMDResponse(
                success=False,
                status="error",
                message=str(e),
                errors=[str(e)],
            )
        except Exception as e:
            logger.error("Claim.MD request error: %s", e)
            return ClaimMDResponse(
                success=False,
                status="error",
                message=str(e),
                errors=[str(e)],
            )

    # ── Claim Submission ──────────────────────────────────────────────

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        """
        Submit a dental claim to Claim.MD.

        claim_data should contain either:
        - "x12": raw X12 837D string (preferred)
        - or JSON fields matching Claim.MD's claim format

        Claim.MD JSON format for dental claims:
        {
            "ClaimType": "D",  # D=Dental, P=Professional
            "PayerID": "...",
            "BillingNPI": "...",
            "BillingTaxID": "...",
            "BillingName": "...",
            "SubscriberID": "...",
            "SubscriberFirstName": "...",
            "SubscriberLastName": "...",
            "SubscriberDOB": "YYYYMMDD",
            "PatientFirstName": "...",
            "PatientLastName": "...",
            "ServiceLines": [
                {
                    "ProcedureCode": "D1110",
                    "ChargeAmount": "150.00",
                    "DateOfService": "YYYYMMDD",
                    "ToothNumber": "",
                    "ToothSurface": "",
                    "DiagnosisPointer": "1",
                }
            ],
            "DiagnosisCodes": ["K02.9"],
            "TotalCharge": "150.00",
            "PlaceOfService": "11",
            "SignatureOnFile": "Y",
        }
        """
        if "x12" in claim_data:
            # Submit raw X12 EDI
            payload = {
                "EDI": claim_data["x12"],
                "Format": "X12",
            }
        else:
            # Submit as Claim.MD JSON
            payload = {
                "Claim": claim_data,
                "Format": "JSON",
            }

        resp = await self._request("POST", "/claim/submit", payload)

        if resp.success:
            tracking_id = resp.data.get("ClaimID", resp.data.get("TrackingID", ""))
            return SubmissionResult(
                tracking_id=tracking_id,
                status="accepted",
                confirmation_number=resp.data.get("ConfirmationNumber"),
                raw_response=resp.data,
            )
        else:
            return SubmissionResult(
                tracking_id="",
                status="rejected",
                error_message=resp.message or "; ".join(resp.errors),
                raw_response=resp.data,
            )

    async def submit_x12(self, x12_content: str) -> SubmissionResult:
        """Submit a raw X12 837D EDI transaction."""
        return await self.submit_claim({"x12": x12_content})

    # ── Claim Status ──────────────────────────────────────────────────

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        """Check the status of a previously submitted claim."""
        resp = await self._request("POST", "/claim/status", {
            "ClaimID": tracking_id,
        })

        if resp.success:
            status_map = {
                "Accepted": "accepted",
                "Rejected": "rejected",
                "Paid": "paid",
                "Denied": "denied",
                "Pending": "pending",
                "Forwarded": "submitted",
            }
            raw_status = resp.data.get("ClaimStatus", "unknown")
            return ClaimStatus(
                tracking_id=tracking_id,
                status=status_map.get(raw_status, raw_status.lower()),
                details=resp.data.get("StatusDetail", resp.message),
            )
        else:
            return ClaimStatus(
                tracking_id=tracking_id,
                status="unknown",
                details=resp.message,
            )

    # ── Eligibility ───────────────────────────────────────────────────

    async def check_eligibility(
        self,
        patient_id: str,
        payer_id: str,
        subscriber_id: str,
        date_of_service: str,
    ) -> EligibilityResult:
        """
        Check patient eligibility via Claim.MD 270/271 transaction.

        Claim.MD handles the X12 270 generation and 271 parsing internally.
        We send JSON, they return structured eligibility data.
        """
        resp = await self._request("POST", "/eligibility/verify", {
            "PayerID": payer_id,
            "SubscriberID": subscriber_id,
            "SubscriberFirstName": "",  # Filled by caller if needed
            "SubscriberLastName": "",
            "SubscriberDOB": "",
            "DateOfService": date_of_service.replace("-", ""),
            "ProviderNPI": "",  # Filled from config
            "ServiceTypeCodes": ["30"],  # 30 = Dental Care
        })

        if not resp.success:
            return EligibilityResult(
                eligible=False,
                coverage_details={"error": resp.message},
            )

        benefits = resp.data.get("Benefits", {})
        return EligibilityResult(
            eligible=resp.data.get("CoverageActive", False),
            annual_maximum=_parse_float(benefits.get("AnnualMaximum")),
            annual_used=_parse_float(benefits.get("AnnualUsed")),
            annual_remaining=_parse_float(benefits.get("AnnualRemaining")),
            deductible=_parse_float(benefits.get("Deductible")),
            deductible_met=benefits.get("DeductibleMet"),
            coverage_details={
                "plan_name": resp.data.get("PlanName", ""),
                "plan_number": resp.data.get("PlanNumber", ""),
                "group_number": resp.data.get("GroupNumber", ""),
                "coverage_effective": resp.data.get("CoverageEffective", ""),
                "coverage_termination": resp.data.get("CoverageTermination", ""),
                "preventive_coverage": benefits.get("PreventiveCoverage", ""),
                "basic_coverage": benefits.get("BasicCoverage", ""),
                "major_coverage": benefits.get("MajorCoverage", ""),
                "orthodontic_coverage": benefits.get("OrthodonticCoverage", ""),
                "waiting_periods": benefits.get("WaitingPeriods", {}),
                "frequency_limitations": benefits.get("FrequencyLimitations", {}),
                "raw_response": resp.data,
            },
        )

    # ── ERA Retrieval ─────────────────────────────────────────────────

    async def get_eras(
        self, from_date: str | None = None, to_date: str | None = None,
    ) -> list[dict]:
        """
        Retrieve ERA (835) files from Claim.MD.

        Returns list of ERA records with payment details.
        """
        payload: dict = {}
        if from_date:
            payload["FromDate"] = from_date.replace("-", "")
        if to_date:
            payload["ToDate"] = to_date.replace("-", "")

        resp = await self._request("POST", "/era/list", payload)

        if resp.success:
            return resp.data.get("ERAs", [])
        return []

    async def get_era_detail(self, era_id: str) -> dict:
        """Get detailed ERA (835) data for a specific remittance."""
        resp = await self._request("POST", "/era/detail", {"ERAID": era_id})
        return resp.data if resp.success else {}

    async def get_era_x12(self, era_id: str) -> str:
        """Get raw X12 835 content for an ERA."""
        resp = await self._request("POST", "/era/x12", {"ERAID": era_id})
        return resp.data.get("X12", "") if resp.success else ""

    # ── Batch Operations ──────────────────────────────────────────────

    async def submit_batch(self, claims: list[dict]) -> list[SubmissionResult]:
        """Submit multiple claims in a batch."""
        results = []
        for claim_data in claims:
            result = await self.submit_claim(claim_data)
            results.append(result)
        return results

    # ── Cleanup ───────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


def _parse_float(value: str | float | None) -> float | None:
    """Safely parse a float value from API response."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ── Other Clearinghouse Adapters (stubs) ──────────────────────────────

class DentalXChangeAdapter(ClearinghouseAdapter):
    """
    DentalXChange clearinghouse adapter (stub).

    DentalXChange is the largest dental-specific clearinghouse.
    - Website: https://www.dentalxchange.com
    - API: SOAP-based with REST wrapper available
    - Formats: X12 837D, proprietary XML
    - Enrollment: Required, contact sales

    TODO: Implement when DentalXChange developer account is available.
    """

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        raise NotImplementedError("DentalXChange adapter not yet implemented")

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        raise NotImplementedError("DentalXChange adapter not yet implemented")

    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult:
        raise NotImplementedError("DentalXChange adapter not yet implemented")


class AvailityAdapter(ClearinghouseAdapter):
    """
    Availity clearinghouse adapter (stub).

    Availity is a large multi-payer health information network.
    - Website: https://www.availity.com
    - API: REST with OAuth 2.0
    - Formats: X12, FHIR
    - Enrollment: Free for providers, register at availity.com

    TODO: Implement when Availity developer credentials are available.
    """

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        raise NotImplementedError("Availity adapter not yet implemented")

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        raise NotImplementedError("Availity adapter not yet implemented")

    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult:
        raise NotImplementedError("Availity adapter not yet implemented")


class TesiaAdapter(ClearinghouseAdapter):
    """
    Tesia (formerly NEA/National Electronic Attachment) adapter (stub).

    Tesia specializes in dental claim attachments and submissions.
    - Website: https://www.tesiahealth.com
    - API: REST
    - Formats: X12, attachment support (images, X-rays)
    - Enrollment: Required

    TODO: Implement when Tesia developer account is available.
    """

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        raise NotImplementedError("Tesia adapter not yet implemented")

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        raise NotImplementedError("Tesia adapter not yet implemented")

    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult:
        raise NotImplementedError("Tesia adapter not yet implemented")


class ChangeHealthcareAdapter(ClearinghouseAdapter):
    """
    Change Healthcare (Optum) adapter (stub).

    One of the largest healthcare clearinghouses.
    - Website: https://www.changehealthcare.com
    - API: REST with OAuth
    - Formats: X12, FHIR
    - Enrollment: Required, enterprise agreement

    TODO: Implement when Change Healthcare developer access is available.
    """

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        raise NotImplementedError("Change Healthcare adapter not yet implemented")

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        raise NotImplementedError("Change Healthcare adapter not yet implemented")

    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult:
        raise NotImplementedError("Change Healthcare adapter not yet implemented")


# ── Adapter Factory ───────────────────────────────────────────────────

CLEARINGHOUSE_REGISTRY: dict[str, type[ClearinghouseAdapter]] = {
    "claim.md": ClaimMDAdapter,
    "claimmd": ClaimMDAdapter,
    "dentalxchange": DentalXChangeAdapter,
    "availity": AvailityAdapter,
    "tesia": TesiaAdapter,
    "nea": TesiaAdapter,
    "change_healthcare": ChangeHealthcareAdapter,
    "optum": ChangeHealthcareAdapter,
}


def get_clearinghouse_adapter(name: str, **kwargs) -> ClearinghouseAdapter:
    """
    Factory to get a clearinghouse adapter by name.

    Usage:
        adapter = get_clearinghouse_adapter("claim.md", config=ClaimMDConfig(...))
        result = await adapter.submit_claim(claim_data)
    """
    adapter_class = CLEARINGHOUSE_REGISTRY.get(name.lower().replace(" ", ""))
    if adapter_class is None:
        available = ", ".join(sorted(set(
            k for k, v in CLEARINGHOUSE_REGISTRY.items()
            if k == k.replace("_", "")  # primary names only
        )))
        raise ValueError(
            f"Unknown clearinghouse: {name}. Available: {available}"
        )
    return adapter_class(**kwargs)
