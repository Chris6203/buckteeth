import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    ClaimCreateRequest,
    ClaimResponse,
    ClaimStatusUpdate,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)
from buckteeth.denials.risk_scorer import DenialRiskScorer
from buckteeth.claims.builder import ClaimBuilder
from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.config import settings
from buckteeth.models.claim import Claim, ClaimNarrative, ClaimProcedure
from buckteeth.models.coding import CodedEncounter
from buckteeth.models.encounter import ClinicalEncounter
from buckteeth.models.patient import Patient

router = APIRouter(prefix="/v1/claims", tags=["claims"])


def _claim_query():
    return (
        select(Claim)
        .options(selectinload(Claim.procedures))
        .options(selectinload(Claim.narratives))
    )


@router.post("", response_model=ClaimResponse, status_code=201)
async def create_claim(
    body: ClaimCreateRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # 1. Load coded encounter with coded procedures
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.id == body.coded_encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded_encounter = result.scalar_one_or_none()
    if coded_encounter is None:
        raise HTTPException(status_code=404, detail="Coded encounter not found")

    # 2. Load clinical encounter
    result = await session.execute(
        select(ClinicalEncounter).where(
            ClinicalEncounter.id == coded_encounter.encounter_id,
            ClinicalEncounter.tenant_id == tenant_id,
        )
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise HTTPException(status_code=404, detail="Clinical encounter not found")

    # 3. Load patient with insurance plans
    result = await session.execute(
        select(Patient)
        .options(selectinload(Patient.insurance_plans))
        .where(
            Patient.id == encounter.patient_id,
            Patient.tenant_id == tenant_id,
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Extract payer info from insurance plans
    primary_plan = next(
        (p for p in patient.insurance_plans if p.plan_type == "primary"), None
    )
    secondary_plan = next(
        (p for p in patient.insurance_plans if p.plan_type == "secondary"), None
    )

    if primary_plan is None:
        raise HTTPException(
            status_code=400, detail="Patient has no primary insurance plan"
        )

    patient_info = {
        "name": f"{patient.first_name} {patient.last_name}",
        "primary_payer_name": primary_plan.payer_name,
        "primary_payer_id": primary_plan.payer_id,
        "primary_subscriber_id": primary_plan.subscriber_id,
        "primary_group_number": primary_plan.group_number,
    }

    # 4. Convert coded procedures to CodeSuggestion for ClaimBuilder
    coded_suggestions = []
    for cp in coded_encounter.coded_procedures:
        coded_suggestions.append(
            CodeSuggestion(
                cdt_code=cp.cdt_code,
                cdt_description=cp.cdt_description,
                tooth_number=cp.tooth_number,
                surfaces=cp.surfaces,
                quadrant=cp.quadrant,
                confidence_score=cp.confidence_score,
                ai_reasoning=cp.ai_reasoning,
                flags=cp.flags or [],
                icd10_codes=cp.icd10_codes or [],
            )
        )

    # 5. Run ClaimBuilder
    builder = ClaimBuilder(api_key=settings.anthropic_api_key)
    claim_detail = await builder.build(
        coded_procedures=coded_suggestions,
        patient_info=patient_info,
        provider_name=encounter.provider_name,
        date_of_service=encounter.date_of_service,
        clinical_notes=encounter.raw_notes or "",
    )

    # 6. Persist Claim
    claim = Claim(
        tenant_id=tenant_id,
        coded_encounter_id=coded_encounter.id,
        patient_id=patient.id,
        provider_name=encounter.provider_name,
        date_of_service=encounter.date_of_service,
        status=claim_detail.status,
        primary_payer_name=primary_plan.payer_name,
        primary_payer_id=primary_plan.payer_id,
        primary_subscriber_id=primary_plan.subscriber_id,
        primary_group_number=primary_plan.group_number,
        secondary_payer_name=secondary_plan.payer_name if secondary_plan else None,
        secondary_payer_id=secondary_plan.payer_id if secondary_plan else None,
        secondary_subscriber_id=secondary_plan.subscriber_id if secondary_plan else None,
        secondary_group_number=secondary_plan.group_number if secondary_plan else None,
        preauth_required=claim_detail.preauth_required,
        total_fee_submitted=claim_detail.total_fee_submitted,
    )
    session.add(claim)
    await session.flush()

    # Persist ClaimProcedures
    for i, cp in enumerate(coded_encounter.coded_procedures):
        proc_detail = claim_detail.procedures[i] if i < len(claim_detail.procedures) else None
        claim_proc = ClaimProcedure(
            tenant_id=tenant_id,
            claim_id=claim.id,
            coded_procedure_id=cp.id,
            cdt_code=cp.cdt_code,
            cdt_description=cp.cdt_description,
            tooth_number=cp.tooth_number,
            surfaces=cp.surfaces,
            quadrant=cp.quadrant,
            fee_submitted=proc_detail.fee_submitted if proc_detail else None,
        )
        session.add(claim_proc)

    # Persist ClaimNarratives
    for narrative in claim_detail.narratives:
        claim_narrative = ClaimNarrative(
            tenant_id=tenant_id,
            claim_id=claim.id,
            cdt_code=narrative.cdt_code,
            narrative_text=narrative.narrative_text,
            generated_by="ai",
            payer_tailored=narrative.payer_tailored,
        )
        session.add(claim_narrative)

    await session.flush()

    # 7. Reload with relationships
    result = await session.execute(
        _claim_query().where(Claim.id == claim.id)
    )
    claim = result.scalar_one()
    return claim


@router.get("", response_model=list[ClaimResponse])
async def list_claims(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    status: str | None = None,
):
    query = _claim_query().where(Claim.tenant_id == tenant_id)
    if status is not None:
        query = query.where(Claim.status == status)
    result = await session.execute(query)
    return result.scalars().unique().all()


@router.get("/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        _claim_query().where(
            Claim.id == claim_id,
            Claim.tenant_id == tenant_id,
        )
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.put("/{claim_id}/status", response_model=ClaimResponse)
async def update_claim_status(
    claim_id: uuid.UUID,
    body: ClaimStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        _claim_query().where(
            Claim.id == claim_id,
            Claim.tenant_id == tenant_id,
        )
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.status = body.status
    await session.flush()
    await session.refresh(claim)

    # Reload with relationships
    result = await session.execute(
        _claim_query().where(Claim.id == claim.id)
    )
    claim = result.scalar_one()
    return claim


@router.post("/{claim_id}/assess-risk", response_model=RiskAssessmentResponse)
async def assess_denial_risk(
    claim_id: uuid.UUID,
    body: RiskAssessmentRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(Claim.id == claim_id, Claim.tenant_id == tenant_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    cdt_codes = [p.cdt_code for p in claim.procedures]

    scorer = DenialRiskScorer(api_key=settings.anthropic_api_key)
    assessment = await scorer.assess(
        cdt_codes=cdt_codes,
        payer_name=claim.primary_payer_name,
        payer_id=claim.primary_payer_id,
        patient_age=body.patient_age,
        provider_name=claim.provider_name,
        date_of_service=claim.date_of_service,
        clinical_notes=f"Claim for {', '.join(cdt_codes)}",
        last_service_dates=body.last_service_dates,
    )

    return RiskAssessmentResponse(
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        risk_factors=assessment.risk_factors,
        recommendations=assessment.recommendations,
    )
