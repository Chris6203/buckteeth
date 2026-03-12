import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.claims.schemas import ClaimDetail, ClaimProcedureDetail, NarrativeResponse
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
                flags=["needs_narrative"],
                icd10_codes=["K02.9"],
            ),
        ],
        encounter_notes="Routine visit",
    )


def _mock_claim_detail():
    return ClaimDetail(
        claim_id=uuid.uuid4(),
        patient_name="Jane Doe",
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        status="draft",
        primary_payer_name="Delta Dental",
        primary_subscriber_id="SUB-001",
        primary_group_number="GRP-001",
        procedures=[
            ClaimProcedureDetail(
                cdt_code="D2393",
                cdt_description="Resin-based composite - three surfaces, posterior",
                tooth_number="14",
                surfaces="MOD",
                quadrant="upper right",
                narrative=NarrativeResponse(
                    cdt_code="D2393",
                    narrative_text="Patient presented with recurrent decay on tooth #14.",
                    payer_tailored=True,
                ),
            ),
        ],
        narratives=[
            NarrativeResponse(
                cdt_code="D2393",
                narrative_text="Patient presented with recurrent decay on tooth #14.",
                payer_tailored=True,
            ),
        ],
        preauth_required=False,
        procedure_count=1,
        has_narratives=True,
        has_preauth=False,
    )


async def _create_patient_with_insurance(client):
    """Create a patient and add insurance plans via direct DB insertion."""
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
    return patient_id


async def _add_insurance_plan(engine, patient_id, tenant_id):
    """Add insurance plan directly to DB since there's no API endpoint for it."""
    from buckteeth.models.patient import InsurancePlan

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        plan = InsurancePlan(
            tenant_id=uuid.UUID(tenant_id),
            patient_id=uuid.UUID(patient_id),
            payer_name="Delta Dental",
            payer_id="DELTA-001",
            subscriber_id="SUB-001",
            group_number="GRP-001",
            plan_type="primary",
        )
        session.add(plan)
        await session.commit()


async def _create_encounter(client, patient_id):
    """Create an encounter with mocked parser."""
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


async def _code_encounter(client, encounter_id):
    """Code an encounter with mocked coding engine."""
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=_mock_coding_result())

        code_resp = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    return code_resp.json()["id"]


@pytest.fixture
async def coded_encounter_id(client, engine):
    """Create patient with insurance, encounter, and coded encounter."""
    patient_id = await _create_patient_with_insurance(client)
    await _add_insurance_plan(engine, patient_id, TENANT_ID)
    encounter_id = await _create_encounter(client, patient_id)
    coded_enc_id = await _code_encounter(client, encounter_id)
    return coded_enc_id


async def test_create_claim(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        response = await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["coded_encounter_id"] == coded_encounter_id
    assert data["status"] == "draft"
    assert data["primary_payer_name"] == "Delta Dental"
    assert data["primary_payer_id"] == "DELTA-001"
    assert data["primary_subscriber_id"] == "SUB-001"
    assert data["primary_group_number"] == "GRP-001"
    assert data["provider_name"] == "Dr. Smith"
    assert len(data["procedures"]) == 1
    assert data["procedures"][0]["cdt_code"] == "D2393"
    assert len(data["narratives"]) == 1
    assert data["narratives"][0]["cdt_code"] == "D2393"
    assert data["narratives"][0]["generated_by"] == "ai"


async def test_list_claims(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    response = await client.get(
        "/v1/claims",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["coded_encounter_id"] == coded_encounter_id


async def test_list_claims_filter_by_status(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    # Filter by status that exists
    response = await client.get(
        "/v1/claims?status=draft",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # Filter by status that doesn't exist
    response = await client.get(
        "/v1/claims?status=submitted",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_get_claim(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        create_resp = await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    claim_id = create_resp.json()["id"]
    get_resp = await client.get(
        f"/v1/claims/{claim_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == claim_id
    assert data["coded_encounter_id"] == coded_encounter_id
    assert len(data["procedures"]) == 1
    assert len(data["narratives"]) == 1


async def test_get_claim_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(
        f"/v1/claims/{random_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404


async def test_update_claim_status(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        create_resp = await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    claim_id = create_resp.json()["id"]
    update_resp = await client.put(
        f"/v1/claims/{claim_id}/status",
        json={"status": "submitted"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "submitted"


async def test_update_claim_status_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.put(
        f"/v1/claims/{random_id}/status",
        json={"status": "submitted"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404
