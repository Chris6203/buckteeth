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


async def test_create_patient(client):
    response = await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    assert response.json()["first_name"] == "Jane"
    assert "id" in response.json()


async def test_get_patient(client):
    create_resp = await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = create_resp.json()["id"]
    get_resp = await client.get(
        f"/v1/patients/{patient_id}", headers={"X-Tenant-ID": TENANT_ID}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["first_name"] == "Jane"


async def test_list_patients(client):
    await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    response = await client.get("/v1/patients", headers={"X-Tenant-ID": TENANT_ID})
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_tenant_isolation(client):
    other_tenant = str(uuid.uuid4())
    await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    response = await client.get("/v1/patients", headers={"X-Tenant-ID": other_tenant})
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_get_patient_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(
        f"/v1/patients/{random_id}", headers={"X-Tenant-ID": TENANT_ID}
    )
    assert response.status_code == 404


async def test_invalid_tenant_id(client):
    response = await client.get(
        "/v1/patients", headers={"X-Tenant-ID": "not-a-uuid"}
    )
    assert response.status_code == 400
