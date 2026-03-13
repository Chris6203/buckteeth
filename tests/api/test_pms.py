import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.database import get_db
from buckteeth.main import app
from buckteeth.models.base import Base

TENANT_ID = str(uuid.uuid4())


@pytest.fixture
async def client(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_pms_status(client):
    response = await client.get("/v1/pms/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["pms_name"] == "MockPMS"


async def test_list_pms_patients(client):
    response = await client.get("/v1/pms/patients")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # Mock has 3 patients


async def test_list_pms_patients_filter(client):
    response = await client.get("/v1/pms/patients?last_name=Smith")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Jane Smith + Maria Smith
    assert all(p["last_name"] == "Smith" for p in data)


async def test_list_pms_encounters(client):
    response = await client.get("/v1/pms/patients/PAT-001/encounters")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # PAT-001 has 2 encounters


async def test_import_patient(client):
    response = await client.post(
        "/v1/pms/import-patient",
        json={"external_id": "PAT-001"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"


async def test_import_encounter(client):
    response = await client.post(
        "/v1/pms/import-encounter",
        json={
            "patient_external_id": "PAT-001",
            "date_of_service": "2026-03-12",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_input_type"] == "pms_import"
    assert len(data["procedures"]) == 3  # 3 procedures in mock ENC-001


async def test_import_patient_not_found(client):
    response = await client.post(
        "/v1/pms/import-patient",
        json={"external_id": "NONEXISTENT"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404
