import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.models.provider import Provider

router = APIRouter(prefix="/v1/providers", tags=["providers"])


# ── Schemas ───────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    first_name: str
    last_name: str
    credentials: str = "DDS"
    npi: str = ""
    specialty: str = "General Dentistry"
    email: str = ""
    phone: str = ""


class ProviderUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    credentials: str | None = None
    npi: str | None = None
    specialty: str | None = None
    email: str | None = None
    phone: str | None = None


class ProviderResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    credentials: str
    npi: str = ""
    specialty: str = ""
    email: str = ""
    phone: str = ""
    is_active: bool
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

    @field_validator("npi", "specialty", "email", "phone", mode="before")
    @classmethod
    def none_to_empty(cls, v: str | None) -> str:
        return v or ""


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    body: ProviderCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    provider = Provider(
        tenant_id=tenant_id,
        first_name=body.first_name,
        last_name=body.last_name,
        credentials=body.credentials,
        npi=body.npi or None,
        specialty=body.specialty or None,
        email=body.email or None,
        phone=body.phone or None,
    )
    session.add(provider)
    await session.flush()
    await session.refresh(provider)
    return provider


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Provider)
        .where(Provider.tenant_id == tenant_id, Provider.is_active.is_(True))
        .order_by(Provider.last_name, Provider.first_name)
    )
    return result.scalars().all()


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.tenant_id == tenant_id
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.tenant_id == tenant_id
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)

    await session.flush()
    await session.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=204)
async def deactivate_provider(
    provider_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.tenant_id == tenant_id
        )
    )
    provider = result.scalar_one_or_none()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.is_active = False
    await session.flush()
