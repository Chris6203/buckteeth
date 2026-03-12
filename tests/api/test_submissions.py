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


async def _create_patient_with_insurance(client, engine):
    """Create a patient and add insurance plan."""
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

    from buckteeth.models.patient import InsurancePlan

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        plan = InsurancePlan(
            tenant_id=uuid.UUID(TENANT_ID),
            patient_id=uuid.UUID(patient_id),
            payer_name="Delta Dental",
            payer_id="DELTA-001",
            subscriber_id="SUB-001",
            group_number="GRP-001",
            plan_type="primary",
        )
        session.add(plan)
        await session.commit()

    return patient_id


async def _create_encounter(client, patient_id):
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
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=_mock_coding_result())

        code_resp = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    return code_resp.json()["id"]


async def _create_claim(client, coded_encounter_id):
    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        instance = MockBuilder.return_value
        instance.build = AsyncMock(return_value=_mock_claim_detail())

        resp = await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_encounter_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    return resp.json()["id"]


async def _create_ready_claim(client, engine):
    """Full pipeline: patient -> encounter -> code -> claim -> set status to ready."""
    patient_id = await _create_patient_with_insurance(client, engine)
    encounter_id = await _create_encounter(client, patient_id)
    coded_enc_id = await _code_encounter(client, encounter_id)
    claim_id = await _create_claim(client, coded_enc_id)

    # Update claim status to "ready"
    await client.put(
        f"/v1/claims/{claim_id}/status",
        json={"status": "ready"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    return claim_id


async def test_submit_claim(client, engine):
    claim_id = await _create_ready_claim(client, engine)

    response = await client.post(
        "/v1/submissions/submit",
        json={"claim_id": claim_id},
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["claim_id"] == claim_id
    assert data["channel"] == "clearinghouse"
    assert data["clearinghouse_name"] == "mock"
    assert data["status"] == "accepted"
    assert data["tracking_number"] is not None
    assert data["confirmation_number"] is not None
    assert data["error_message"] is None


async def test_submit_claim_not_ready(client, engine):
    """Submitting a claim that is not in 'ready' status should fail."""
    patient_id = await _create_patient_with_insurance(client, engine)
    encounter_id = await _create_encounter(client, patient_id)
    coded_enc_id = await _code_encounter(client, encounter_id)
    claim_id = await _create_claim(client, coded_enc_id)
    # claim is in "draft" status, not "ready"

    response = await client.post(
        "/v1/submissions/submit",
        json={"claim_id": claim_id},
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 400
    assert "ready" in response.json()["detail"]


async def test_list_submissions(client, engine):
    claim_id = await _create_ready_claim(client, engine)

    await client.post(
        "/v1/submissions/submit",
        json={"claim_id": claim_id},
        headers={"X-Tenant-ID": TENANT_ID},
    )

    response = await client.get(
        "/v1/submissions",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["claim_id"] == claim_id


async def test_get_submission(client, engine):
    claim_id = await _create_ready_claim(client, engine)

    submit_resp = await client.post(
        "/v1/submissions/submit",
        json={"claim_id": claim_id},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    submission_id = submit_resp.json()["id"]

    response = await client.get(
        f"/v1/submissions/{submission_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == submission_id
    assert data["claim_id"] == claim_id


async def test_get_submission_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(
        f"/v1/submissions/{random_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404


async def test_check_eligibility(client):
    response = await client.post(
        "/v1/submissions/eligibility",
        json={
            "patient_id": str(uuid.uuid4()),
            "payer_id": "DELTA-001",
            "subscriber_id": "SUB-001",
            "date_of_service": "2026-03-12",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["eligible"] is True
    assert data["annual_maximum"] == 2000.0
    assert data["annual_used"] == 450.0
    assert data["annual_remaining"] == 1550.0
    assert data["deductible"] == 50.0
    assert data["deductible_met"] == 1.0


async def test_batch_submit(client, engine):
    claim_id_1 = await _create_ready_claim(client, engine)
    claim_id_2 = await _create_ready_claim(client, engine)

    response = await client.post(
        "/v1/submissions/batch-submit",
        json={"claim_ids": [claim_id_1, claim_id_2]},
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["claim_id"] == claim_id_1
    assert data[1]["claim_id"] == claim_id_2
    assert data[0]["status"] == "accepted"
    assert data[1]["status"] == "accepted"
