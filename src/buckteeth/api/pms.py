import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    PMSConnectionResponse, PMSEncounterResponse, PMSImportEncounterRequest,
    PMSImportPatientRequest, PMSPatientResponse, EncounterResponse, PatientResponse,
)
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.patient import Patient, InsurancePlan
from buckteeth.pms.adapters import MockPMSAdapter

router = APIRouter(prefix="/v1/pms", tags=["pms"])


def _get_adapter():
    return MockPMSAdapter()


@router.get("/status", response_model=PMSConnectionResponse)
async def check_pms_status():
    adapter = _get_adapter()
    status = await adapter.authenticate({})
    return PMSConnectionResponse(
        connected=status.connected,
        pms_name=status.pms_name,
        version=status.version,
        last_sync=status.last_sync,
    )


@router.get("/patients", response_model=list[PMSPatientResponse])
async def list_pms_patients(
    last_name: str | None = Query(default=None),
):
    adapter = _get_adapter()
    filters = {}
    if last_name:
        filters["last_name"] = last_name
    patients = await adapter.pull_patients(**filters)
    return [
        PMSPatientResponse(
            external_id=p.external_id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            gender=p.gender,
            primary_payer_name=p.primary_payer_name,
            primary_subscriber_id=p.primary_subscriber_id,
        )
        for p in patients
    ]


@router.get("/patients/{external_id}/encounters", response_model=list[PMSEncounterResponse])
async def list_pms_encounters(external_id: str):
    adapter = _get_adapter()
    history = await adapter.pull_treatment_history(external_id)
    return [
        PMSEncounterResponse(
            external_id=e.external_id,
            patient_external_id=e.patient_external_id,
            provider_name=e.provider_name,
            date_of_service=e.date_of_service,
            procedure_count=len(e.procedures),
            notes=e.notes,
        )
        for e in history.encounters
    ]


@router.post("/import-patient", response_model=PatientResponse, status_code=201)
async def import_patient_from_pms(
    body: PMSImportPatientRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    adapter = _get_adapter()
    pms_patients = await adapter.pull_patients(external_id=body.external_id)
    if not pms_patients:
        raise HTTPException(status_code=404, detail="Patient not found in PMS")
    pms_patient = pms_patients[0]

    patient = Patient(
        tenant_id=tenant_id,
        first_name=pms_patient.first_name,
        last_name=pms_patient.last_name,
        date_of_birth=pms_patient.date_of_birth,
        gender=pms_patient.gender,
    )
    session.add(patient)
    await session.flush()

    if pms_patient.primary_payer_name:
        plan = InsurancePlan(
            tenant_id=tenant_id,
            patient_id=patient.id,
            payer_name=pms_patient.primary_payer_name,
            payer_id=pms_patient.primary_payer_id or "",
            subscriber_id=pms_patient.primary_subscriber_id or "",
            group_number=pms_patient.primary_group_number or "",
            plan_type="primary",
        )
        session.add(plan)
        await session.flush()

    await session.refresh(patient)
    return patient


@router.post("/import-encounter", response_model=EncounterResponse, status_code=201)
async def import_encounter_from_pms(
    body: PMSImportEncounterRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    adapter = _get_adapter()
    pms_encounter = await adapter.pull_encounter(
        body.patient_external_id, body.date_of_service,
    )
    if pms_encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found in PMS")

    # For import, we need a patient in our system
    pms_patients = await adapter.pull_patients(external_id=body.patient_external_id)
    if not pms_patients:
        raise HTTPException(status_code=404, detail="Patient not found in PMS")
    pms_patient = pms_patients[0]

    patient = Patient(
        tenant_id=tenant_id,
        first_name=pms_patient.first_name,
        last_name=pms_patient.last_name,
        date_of_birth=pms_patient.date_of_birth,
        gender=pms_patient.gender,
    )
    session.add(patient)
    await session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_name=pms_encounter.provider_name,
        date_of_service=pms_encounter.date_of_service,
        raw_notes=pms_encounter.notes or "",
        raw_input_type="pms_import",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in pms_encounter.procedures:
        clinical_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers=[int(proc.tooth_number)] if proc.tooth_number and proc.tooth_number.isdigit() else None,
            surfaces=list(proc.surfaces) if proc.surfaces else None,
            quadrant=None,
            diagnosis=None,
        )
        session.add(clinical_proc)

    await session.flush()

    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()
