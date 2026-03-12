import uuid

from buckteeth.submission.adapters import ClearinghouseAdapter, SubmissionResult, ClaimStatus


class SubmissionGateway:
    def __init__(self, adapter: ClearinghouseAdapter) -> None:
        self._adapter = adapter
        self._idempotency_cache: dict[str, SubmissionResult] = {}

    async def submit(
        self,
        claim_id: uuid.UUID,
        claim_data: dict,
        idempotency_key: str | None = None,
    ) -> SubmissionResult:
        if idempotency_key and idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        result = await self._adapter.submit_claim(claim_data)

        if idempotency_key:
            self._idempotency_cache[idempotency_key] = result

        return result

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        return await self._adapter.check_status(tracking_id)

    async def batch_submit(
        self, claims: list[tuple[uuid.UUID, dict]]
    ) -> list[SubmissionResult]:
        results = []
        for claim_id, claim_data in claims:
            result = await self.submit(claim_id, claim_data)
            results.append(result)
        return results
