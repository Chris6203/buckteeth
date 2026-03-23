import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import EncounterFromNotesRequest, EncounterResponse
from buckteeth.config import settings
from buckteeth.coding.documentation_checker import check_documentation
from buckteeth.coding.documentation_templates import generate_documentation_template
from buckteeth.coding.image_verifier import ImageProcedureVerifier
from buckteeth.coding.pre_submission_validator import validate_pre_submission
from buckteeth.ingestion.image_analyzer import ImageAnalyzer
from buckteeth.ingestion.image_quality import validate_image_quality
from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.ingestion.transcription import MockTranscriptionService
from buckteeth.models.coding import CodedEncounter, CodedProcedure
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


@router.post("/{encounter_id}/verify-images")
async def verify_images_against_procedures(
    encounter_id: uuid.UUID,
    image: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Verify that uploaded images support the coded procedures for this encounter.

    Returns per-procedure verification status, missed findings in the image,
    and an overall documentation strength assessment.
    """
    # Get the coded encounter
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.encounter_id == encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded = result.scalar_one_or_none()
    if coded is None:
        raise HTTPException(
            status_code=404,
            detail="No coded encounter found. Code the encounter first.",
        )

    # Get the original encounter for clinical notes context
    enc_result = await session.execute(
        select(ClinicalEncounter).where(
            ClinicalEncounter.id == encounter_id,
            ClinicalEncounter.tenant_id == tenant_id,
        )
    )
    encounter = enc_result.scalar_one_or_none()

    # Build procedure list for verification
    procedures = [
        {
            "cdt_code": cp.cdt_code,
            "cdt_description": cp.cdt_description,
            "tooth_number": cp.tooth_number,
            "surfaces": cp.surfaces,
        }
        for cp in coded.coded_procedures
    ]

    image_data = await image.read()
    media_type = image.content_type or "image/png"

    verifier = ImageProcedureVerifier(api_key=settings.anthropic_api_key)
    verification = await verifier.verify(
        image_data=image_data,
        media_type=media_type,
        coded_procedures=procedures,
        clinical_notes=encounter.raw_notes if encounter else None,
    )

    return verification.to_dict()


@router.post("/{encounter_id}/check-documentation")
async def check_documentation_requirements(
    encounter_id: uuid.UUID,
    has_images: bool = Form(default=False),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Check whether coded procedures have required supporting documentation.
    Returns alerts for missing X-rays, narratives, perio charting, etc.
    """
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.encounter_id == encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded = result.scalar_one_or_none()
    if coded is None:
        raise HTTPException(status_code=404, detail="No coded encounter found.")

    # Get original encounter to check if notes exist
    enc_result = await session.execute(
        select(ClinicalEncounter).where(
            ClinicalEncounter.id == encounter_id,
            ClinicalEncounter.tenant_id == tenant_id,
        )
    )
    encounter = enc_result.scalar_one_or_none()
    has_narrative = bool(encounter and encounter.raw_notes and len(encounter.raw_notes) > 10)

    procedures = [
        {
            "cdt_code": cp.cdt_code,
            "cdt_description": cp.cdt_description,
            "tooth_number": cp.tooth_number,
            "surfaces": cp.surfaces,
        }
        for cp in coded.coded_procedures
    ]

    check = check_documentation(
        coded_procedures=procedures,
        has_images=has_images,
        has_narrative=has_narrative,
    )

    return check.to_dict()


@router.post("/{encounter_id}/validate")
async def validate_for_submission(
    encounter_id: uuid.UUID,
    payer_id: str = Form(default=""),
    has_images: bool = Form(default=False),
    patient_history: str = Form(default="[]"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Run comprehensive pre-submission validation on a coded encounter.
    Checks frequency rules, documentation, payer-specific rules, and known denial patterns.
    """
    import json as _json

    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(
            CodedEncounter.encounter_id == encounter_id,
            CodedEncounter.tenant_id == tenant_id,
        )
    )
    coded = result.scalar_one_or_none()
    if coded is None:
        raise HTTPException(status_code=404, detail="No coded encounter found.")

    enc_result = await session.execute(
        select(ClinicalEncounter).where(
            ClinicalEncounter.id == encounter_id,
            ClinicalEncounter.tenant_id == tenant_id,
        )
    )
    encounter = enc_result.scalar_one_or_none()

    procedures = [
        {
            "cdt_code": cp.cdt_code,
            "cdt_description": cp.cdt_description,
            "tooth_number": cp.tooth_number,
            "surfaces": cp.surfaces,
            "fee_submitted": None,
        }
        for cp in coded.coded_procedures
    ]

    try:
        history = _json.loads(patient_history) if patient_history else []
    except _json.JSONDecodeError:
        history = []

    validation = validate_pre_submission(
        coded_procedures=procedures,
        payer_id=payer_id or None,
        patient_history=history,
        has_images=has_images,
        has_narrative=bool(encounter and encounter.raw_notes and len(encounter.raw_notes) > 10),
    )

    return validation.to_dict()


@router.post("/{encounter_id}/documentation-template")
async def get_documentation_template(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate a smart documentation template based on parsed procedures.
    Tells the dentist exactly what images, measurements, and narrative
    details they need to provide for each procedure.
    """
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

    procedures = [
        {
            "description": p.description,
            "tooth_numbers": p.tooth_numbers,
            "surfaces": p.surfaces,
            "quadrant": p.quadrant,
            "diagnosis": p.diagnosis,
        }
        for p in encounter.procedures
    ]

    template = generate_documentation_template(procedures)
    return template.to_dict()


@router.post("/check-image-quality")
async def check_image_quality(
    image: UploadFile = File(...),
):
    """
    Validate image quality before processing. Returns immediately with any
    issues that could cause insurance rejection (low resolution, wrong format,
    file too small/large, etc.). No AI call — pure file inspection.
    """
    image_data = await image.read()
    result = validate_image_quality(
        image_data=image_data,
        media_type=image.content_type or "unknown",
        filename=image.filename,
    )
    return result.to_dict()


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
