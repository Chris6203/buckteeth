import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.database import get_db
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure
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


@pytest.fixture
async def patient_id(client):
    """Create a patient and return their ID."""
    resp = await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    return resp.json()["id"]


def _mock_parsed():
    return ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="MOD composite restoration",
                tooth_numbers=[14],
                surfaces=["M", "O", "D"],
                quadrant="upper right",
                diagnosis="recurrent decay",
            ),
        ],
        notes="Routine visit",
    )


async def test_create_encounter_from_notes(client, patient_id):
    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=_mock_parsed())

        response = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "MOD composite on #14 for recurrent decay",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["raw_input_type"] == "text"
    assert data["status"] == "parsed"
    assert len(data["procedures"]) == 1
    assert data["procedures"][0]["description"] == "MOD composite restoration"


async def test_get_encounter(client, patient_id):
    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=_mock_parsed())

        create_resp = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "MOD composite on #14",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    encounter_id = create_resp.json()["id"]
    get_resp = await client.get(
        f"/v1/encounters/{encounter_id}", headers={"X-Tenant-ID": TENANT_ID}
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == encounter_id
    assert len(get_resp.json()["procedures"]) == 1


async def test_get_encounter_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(
        f"/v1/encounters/{random_id}", headers={"X-Tenant-ID": TENANT_ID}
    )
    assert response.status_code == 404


async def test_encounter_tenant_isolation(client, patient_id):
    other_tenant = str(uuid.uuid4())
    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=_mock_parsed())

        create_resp = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "MOD composite on #14",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    encounter_id = create_resp.json()["id"]
    get_resp = await client.get(
        f"/v1/encounters/{encounter_id}", headers={"X-Tenant-ID": other_tenant}
    )
    assert get_resp.status_code == 404
