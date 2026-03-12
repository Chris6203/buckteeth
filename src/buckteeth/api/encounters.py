import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import EncounterFromNotesRequest, EncounterResponse
from buckteeth.config import settings
from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure

router = APIRouter(prefix="/v1/encounters", tags=["encounters"])


@router.post("/from-notes", response_model=EncounterResponse, status_code=201)
async def create_encounter_from_notes(
    body: EncounterFromNotesRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    parser = ClinicalNoteParser(api_key=settings.anthropic_api_key)
    parsed = await parser.parse(body.notes)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=body.patient_id,
        provider_name=body.provider_name,
        date_of_service=body.date_of_service,
        raw_notes=body.notes,
        raw_input_type="text",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in parsed.procedures:
        clinical_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers=proc.tooth_numbers,
            surfaces=proc.surfaces,
            quadrant=proc.quadrant,
            diagnosis=proc.diagnosis,
        )
        session.add(clinical_proc)

    await session.flush()
    await session.refresh(encounter)

    # Reload with procedures eagerly
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    encounter = result.scalar_one()
    return encounter


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
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
    return encounter
