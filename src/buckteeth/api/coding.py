import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    CodedEncounterResponse,
    CodeEncounterRequest,
    OverrideProcedureRequest,
)
from buckteeth.coding.engine import CodingEngine
from buckteeth.config import settings
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure

router = APIRouter(prefix="/v1/encounters", tags=["coding"])


@router.post(
    "/{encounter_id}/code", response_model=CodedEncounterResponse, status_code=201
)
async def code_encounter(
    encounter_id: uuid.UUID,
    body: CodeEncounterRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Load the encounter with its procedures
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(
            ClinicalEncounter.id == encounter_id,
            ClinicalEncounter.tenant_id == tenant_id,
        )
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Convert DB procedures to ingestion schemas for the coding engine
    parsed_procedures = []
    for proc in encounter.procedures:
        parsed_procedures.append(
            ParsedProcedure(
                description=proc.description,
                tooth_numbers=proc.tooth_numbers,
                surfaces=proc.surfaces,
                quadrant=proc.quadrant,
                diagnosis=proc.diagnosis,
            )
        )

    parsed_encounter = ParsedEncounter(procedures=parsed_procedures)

    engine = CodingEngine(api_key=settings.anthropic_api_key)
    coding_result = await engine.code_encounter(
        parsed_encounter, payer_id=body.payer_id
    )

    # Save coded encounter
    coded_encounter = CodedEncounter(
        tenant_id=tenant_id,
        encounter_id=encounter_id,
        review_status="pending",
    )
    session.add(coded_encounter)
    await session.flush()

    # Save coded procedures, mapping back to clinical procedures
    clinical_procs = encounter.procedures
    for i, suggestion in enumerate(coding_result.suggestions):
        # Map suggestion back to its clinical procedure
        clinical_proc_id = (
            clinical_procs[i].id if i < len(clinical_procs) else clinical_procs[-1].id
        )
        coded_proc = CodedProcedure(
            tenant_id=tenant_id,
            coded_encounter_id=coded_encounter.id,
            clinical_procedure_id=clinical_proc_id,
            cdt_code=suggestion.cdt_code,
            cdt_description=suggestion.cdt_description,
            tooth_number=suggestion.tooth_number,
            surfaces=suggestion.surfaces,
            quadrant=suggestion.quadrant,
            confidence_score=suggestion.confidence_score,
            ai_reasoning=suggestion.ai_reasoning,
            flags=suggestion.flags,
            icd10_codes=suggestion.icd10_codes,
        )
        session.add(coded_proc)

    await session.flush()

    # Reload with coded procedures
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(CodedEncounter.id == coded_encounter.id)
    )
    coded_encounter = result.scalar_one()
    return coded_encounter


@router.get("/{encounter_id}/coded", response_model=CodedEncounterResponse)
async def get_coded_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.encounter_id == encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded_encounter = result.scalar_one_or_none()
    if coded_encounter is None:
        raise HTTPException(status_code=404, detail="Coded encounter not found")
    return coded_encounter


@router.post("/{encounter_id}/coded/approve", response_model=CodedEncounterResponse)
async def approve_coded_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.encounter_id == encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded_encounter = result.scalar_one_or_none()
    if coded_encounter is None:
        raise HTTPException(status_code=404, detail="Coded encounter not found")

    coded_encounter.review_status = "approved"
    await session.flush()
    await session.refresh(coded_encounter)
    return coded_encounter
