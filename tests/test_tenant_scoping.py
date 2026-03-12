import uuid

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from buckteeth.models.base import Base, TenantScopedBase


class FakeItem(TenantScopedBase):
    __tablename__ = "fake_items"
    name: Mapped[str] = mapped_column(String(100))


@pytest.fixture(autouse=True)
async def create_table(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_tenant_scoped_model_requires_tenant_id(db_session):
    tenant_id = uuid.uuid4()
    item = FakeItem(tenant_id=tenant_id, name="test")
    db_session.add(item)
    await db_session.flush()
    assert item.id is not None
    assert item.tenant_id == tenant_id


async def test_tenant_scoped_model_has_timestamps(db_session):
    tenant_id = uuid.uuid4()
    item = FakeItem(tenant_id=tenant_id, name="test")
    db_session.add(item)
    await db_session.flush()
    assert item.created_at is not None
    assert item.updated_at is not None
