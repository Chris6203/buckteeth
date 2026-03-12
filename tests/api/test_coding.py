import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.coding.schemas import CodeSuggestion, CodingResult
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


def _mock_coding_result():
    return CodingResult(
        suggestions=[
            CodeSuggestion(
                cdt_code="D2393",
                cdt_description="Resin-based composite - three surfaces, posterior",
                tooth_number="14",
                surfaces="MOD",
                quadrant="upper right",
                confidence_score=95,
                ai_reasoning="Three-surface posterior composite matches D2393",
                flags=[],
                icd10_codes=["K02.9"],
            ),
        ],
        encounter_notes="Routine visit",
    )


@pytest.fixture
async def encounter_id(client):
    """Create a patient and encounter, return encounter ID."""
    # Create patient
    patient_resp = await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = patient_resp.json()["id"]

    # Create encounter
    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=_mock_parsed())

        enc_resp = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "MOD composite on #14 for recurrent decay",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    return enc_resp.json()["id"]


async def test_code_encounter(client, encounter_id):
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=_mock_coding_result())

        response = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["encounter_id"] == encounter_id
    assert data["review_status"] == "pending"
    assert len(data["coded_procedures"]) == 1
    assert data["coded_procedures"][0]["cdt_code"] == "D2393"
    assert data["coded_procedures"][0]["confidence_score"] == 95


async def test_get_coded_encounter(client, encounter_id):
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=_mock_coding_result())

        await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    get_resp = await client.get(
        f"/v1/encounters/{encounter_id}/coded",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["encounter_id"] == encounter_id
    assert len(get_resp.json()["coded_procedures"]) == 1


async def test_approve_coded_encounter(client, encounter_id):
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=_mock_coding_result())

        await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    approve_resp = await client.post(
        f"/v1/encounters/{encounter_id}/coded/approve",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["review_status"] == "approved"


async def test_code_encounter_not_found(client):
    random_id = str(uuid.uuid4())
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        response = await client.post(
            f"/v1/encounters/{random_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    assert response.status_code == 404


async def test_get_coded_encounter_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(
        f"/v1/encounters/{random_id}/coded",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404
