import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    InsurancePlanCreate,
    InsurancePlanResponse,
    PatientCreate,
    PatientResponse,
)
from buckteeth.models.patient import InsurancePlan, Patient

router = APIRouter(prefix="/v1/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    body: PatientCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    patient = Patient(
        tenant_id=tenant_id,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
    )
    session.add(patient)
    await session.flush()

    # Re-query with eager load to avoid lazy load error in async context
    result = await session.execute(
        select(Patient)
        .options(selectinload(Patient.insurance_plans))
        .where(Patient.id == patient.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    q: str | None = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    query = (
        select(Patient)
        .where(Patient.tenant_id == tenant_id)
        .options(selectinload(Patient.insurance_plans))
    )
    if q:
        search = f"%{q}%"
        query = query.where(
            Patient.first_name.ilike(search) | Patient.last_name.ilike(search)
        )
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Patient)
        .where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
        .options(selectinload(Patient.insurance_plans))
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post(
    "/{patient_id}/insurance",
    response_model=InsurancePlanResponse,
    status_code=201,
)
async def add_insurance_plan(
    patient_id: uuid.UUID,
    body: InsurancePlanCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    plan = InsurancePlan(
        tenant_id=tenant_id,
        patient_id=patient_id,
        payer_name=body.payer_name,
        payer_id=body.payer_id,
        subscriber_id=body.subscriber_id,
        group_number=body.group_number,
        plan_type=body.plan_type,
    )
    session.add(plan)
    await session.flush()
    await session.refresh(plan)
    return plan


@router.get("/{patient_id}/insurance", response_model=list[InsurancePlanResponse])
async def list_insurance_plans(
    patient_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    result = await session.execute(
        select(InsurancePlan).where(InsurancePlan.patient_id == patient_id)
    )
    return result.scalars().all()


@router.delete("/{patient_id}/insurance/{plan_id}", status_code=204)
async def remove_insurance_plan(
    patient_id: uuid.UUID,
    plan_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(InsurancePlan).where(
            InsurancePlan.id == plan_id,
            InsurancePlan.patient_id == patient_id,
        )
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Insurance plan not found")

    await session.delete(plan)
    await session.flush()
