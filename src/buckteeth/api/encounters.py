import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import EncounterFromNotesRequest, EncounterResponse
from buckteeth.config import settings
from buckteeth.ingestion.image_analyzer import ImageAnalyzer
from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.ingestion.transcription import MockTranscriptionService
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


@router.post("/from-image", response_model=EncounterResponse, status_code=201)
async def create_encounter_from_image(
    patient_id: uuid.UUID = Form(...),
    provider_name: str = Form(...),
    date_of_service: str = Form(...),
    context: str = Form(default=""),
    image: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    image_data = await image.read()
    media_type = image.content_type or "image/png"

    analyzer = ImageAnalyzer(api_key=settings.anthropic_api_key)
    parsed = await analyzer.analyze(image_data, media_type, context or None)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient_id,
        provider_name=provider_name,
        date_of_service=date_of_service,
        raw_notes=f"[Image analysis] {context}" if context else "[Image analysis]",
        raw_input_type="image",
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
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()


@router.post("/from-voice", response_model=EncounterResponse, status_code=201)
async def create_encounter_from_voice(
    patient_id: uuid.UUID = Form(...),
    provider_name: str = Form(...),
    date_of_service: str = Form(...),
    audio: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    audio_data = await audio.read()
    audio_format = "wav"
    if audio.content_type:
        if "mp3" in audio.content_type:
            audio_format = "mp3"
        elif "ogg" in audio.content_type:
            audio_format = "ogg"

    transcription_service = MockTranscriptionService()
    transcription = await transcription_service.transcribe(audio_data, audio_format)

    parser = ClinicalNoteParser(api_key=settings.anthropic_api_key)
    parsed = await parser.parse(transcription.text)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient_id,
        provider_name=provider_name,
        date_of_service=date_of_service,
        raw_notes=transcription.text,
        raw_input_type="voice",
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
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()
