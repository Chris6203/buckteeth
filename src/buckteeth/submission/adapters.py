import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SubmissionResult:
    tracking_id: str
    status: str
    confirmation_number: str | None = None
    error_message: str | None = None
    raw_response: dict | None = None


@dataclass
class ClaimStatus:
    tracking_id: str
    status: str
    details: str | None = None


@dataclass
class EligibilityResult:
    eligible: bool
    annual_maximum: float | None = None
    annual_used: float | None = None
    annual_remaining: float | None = None
    deductible: float | None = None
    deductible_met: bool | None = None
    coverage_details: dict | None = None


class ClearinghouseAdapter(ABC):
    @abstractmethod
    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        ...

    @abstractmethod
    async def check_status(self, tracking_id: str) -> ClaimStatus:
        ...

    @abstractmethod
    async def check_eligibility(
        self,
        patient_id: str,
        payer_id: str,
        subscriber_id: str,
        date_of_service: str,
    ) -> EligibilityResult:
        ...


class MockClearinghouseAdapter(ClearinghouseAdapter):
    def __init__(self) -> None:
        self._submissions: dict[str, dict] = {}

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        tracking_id = f"TRK-{uuid.uuid4().hex[:8].upper()}"
        self._submissions[tracking_id] = {
            "claim_data": claim_data,
            "status": "accepted",
        }
        return SubmissionResult(
            tracking_id=tracking_id,
            status="accepted",
            confirmation_number=f"CONF-{uuid.uuid4().hex[:8].upper()}",
        )

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        entry = self._submissions.get(tracking_id)
        if entry is None:
            return ClaimStatus(
                tracking_id=tracking_id,
                status="unknown",
                details="No submission found for this tracking ID",
            )
        return ClaimStatus(
            tracking_id=tracking_id,
            status=entry["status"],
            details="Claim accepted by payer",
        )

    async def check_eligibility(
        self,
        patient_id: str,
        payer_id: str,
        subscriber_id: str,
        date_of_service: str,
    ) -> EligibilityResult:
        return EligibilityResult(
            eligible=True,
            annual_maximum=2000.0,
            annual_used=450.0,
            annual_remaining=1550.0,
            deductible=50.0,
            deductible_met=True,
            coverage_details={
                "patient_id": patient_id,
                "payer_id": payer_id,
                "subscriber_id": subscriber_id,
                "date_of_service": date_of_service,
            },
        )
