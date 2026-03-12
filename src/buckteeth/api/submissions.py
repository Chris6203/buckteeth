import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    EligibilityCheckResponse,
    EligibilityRequest,
    SubmissionResponse,
    SubmitBatchRequest,
    SubmitClaimRequest,
)
from buckteeth.models.claim import Claim, ClaimProcedure
from buckteeth.models.submission import SubmissionRecord
from buckteeth.submission.adapters import MockClearinghouseAdapter
from buckteeth.submission.gateway import SubmissionGateway

router = APIRouter(prefix="/v1/submissions", tags=["submissions"])


async def _submit_single_claim(
    claim_id: uuid.UUID,
    tenant_id: uuid.UUID,
    session: AsyncSession,
) -> SubmissionRecord:
    # 1. Load and verify claim
    result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(
            Claim.id == claim_id,
            Claim.tenant_id == tenant_id,
        )
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    if claim.status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Claim status must be 'ready' to submit, got '{claim.status}'",
        )

    # 2. Build claim_data dict from procedures
    procedures_data = []
    for proc in claim.procedures:
        procedures_data.append({
            "cdt_code": proc.cdt_code,
            "cdt_description": proc.cdt_description,
            "tooth_number": proc.tooth_number,
            "surfaces": proc.surfaces,
            "quadrant": proc.quadrant,
            "fee_submitted": proc.fee_submitted,
        })

    claim_data = {
        "claim_id": str(claim.id),
        "patient_id": str(claim.patient_id),
        "provider_name": claim.provider_name,
        "date_of_service": claim.date_of_service,
        "primary_payer_name": claim.primary_payer_name,
        "primary_payer_id": claim.primary_payer_id,
        "primary_subscriber_id": claim.primary_subscriber_id,
        "primary_group_number": claim.primary_group_number,
        "procedures": procedures_data,
    }

    # 3. Submit via gateway
    adapter = MockClearinghouseAdapter()
    gateway = SubmissionGateway(adapter=adapter)
    idempotency_key = f"claim-{claim.id}"
    submission_result = await gateway.submit(
        claim_id=claim.id,
        claim_data=claim_data,
        idempotency_key=idempotency_key,
    )

    # 4. Create SubmissionRecord
    record = SubmissionRecord(
        tenant_id=tenant_id,
        claim_id=claim.id,
        channel="clearinghouse",
        clearinghouse_name="mock",
        tracking_number=submission_result.tracking_id,
        confirmation_number=submission_result.confirmation_number,
        status=submission_result.status,
        error_message=submission_result.error_message,
        response_data=submission_result.raw_response,
        idempotency_key=idempotency_key,
    )
    session.add(record)

    # 5. Update claim status
    claim.status = "submitted"

    await session.flush()
    await session.refresh(record)
    return record


@router.post("/submit", response_model=SubmissionResponse, status_code=201)
async def submit_claim(
    body: SubmitClaimRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    record = await _submit_single_claim(body.claim_id, tenant_id, session)
    return record


@router.post("/batch-submit", response_model=list[SubmissionResponse], status_code=201)
async def batch_submit(
    body: SubmitBatchRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    results = []
    for claim_id in body.claim_ids:
        record = await _submit_single_claim(claim_id, tenant_id, session)
        results.append(record)
    return results


@router.get("", response_model=list[SubmissionResponse])
async def list_submissions(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SubmissionRecord).where(SubmissionRecord.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SubmissionRecord).where(
            SubmissionRecord.id == submission_id,
            SubmissionRecord.tenant_id == tenant_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return record


@router.post("/eligibility", response_model=EligibilityCheckResponse)
async def check_eligibility(
    body: EligibilityRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    adapter = MockClearinghouseAdapter()
    elig_result = await adapter.check_eligibility(
        patient_id=str(body.patient_id),
        payer_id=body.payer_id,
        subscriber_id=body.subscriber_id,
        date_of_service=body.date_of_service,
    )
    return EligibilityCheckResponse(
        eligible=elig_result.eligible,
        annual_maximum=elig_result.annual_maximum,
        annual_used=elig_result.annual_used,
        annual_remaining=elig_result.annual_remaining,
        deductible=elig_result.deductible,
        deductible_met=elig_result.deductible_met,
    )
