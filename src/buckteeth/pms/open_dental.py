"""Open Dental PMS Adapter.

Open Dental exposes a REST API (typically at localhost:30222/api/v1 on the
office server). This adapter implements the PMSAdapter interface against
the Open Dental API.

Documentation: https://www.opendental.com/site/apispecification.html

Requires:
- Open Dental 22.1+ with API enabled
- API key generated from Open Dental Setup > Advanced Setup > API
"""

from buckteeth.pms.adapters import PMSAdapter
from buckteeth.pms.schemas import (
    PMSClaimResult, PMSConnectionStatus, PMSEncounter,
    PMSFeeSchedule, PMSPatient, PMSTreatmentHistory,
)


class OpenDentalAdapter(PMSAdapter):
    """Open Dental REST API adapter (Tier 1 integration)."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        # TODO: GET {base_url}/patients?limit=1 to verify connectivity
        raise NotImplementedError(
            "Open Dental integration pending API access. "
            "Configure base_url and api_key in settings."
        )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        # TODO: GET {base_url}/patients with query params
        raise NotImplementedError("Open Dental pull_patients pending implementation")

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        # TODO: GET {base_url}/procedurelogs?PatNum={id}&ProcDate={date}
        raise NotImplementedError("Open Dental pull_encounter pending implementation")

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        # TODO: GET {base_url}/procedurelogs?PatNum={id}
        raise NotImplementedError("Open Dental pull_treatment_history pending implementation")

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        # TODO: POST {base_url}/claims with claim body
        raise NotImplementedError("Open Dental push_coded_claim pending implementation")

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        # TODO: GET {base_url}/feescheds?InsPayPlanNum={id}
        raise NotImplementedError("Open Dental get_fee_schedule pending implementation")
