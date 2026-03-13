import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.claims.schemas import ClaimDetail, ClaimProcedureDetail, NarrativeResponse
from buckteeth.coding.schemas import CodeSuggestion, CodingResult
from buckteeth.database import get_db
from buckteeth.denials.schemas import AppealResponse as AppealGenResponse
from buckteeth.denials.schemas import CommissionerLetterResponse as CommLetterGenResponse
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


async def _create_claim_for_denial(client, engine):
    """Full pipeline: patient -> encounter -> code -> claim (draft status is OK for denial)."""
    patient_id = await _create_patient_with_insurance(client, engine)
    encounter_id = await _create_encounter(client, patient_id)
    coded_enc_id = await _code_encounter(client, encounter_id)
    claim_id = await _create_claim(client, coded_enc_id)
    return claim_id


async def _create_denial(client, engine):
    """Create a claim and then a denial record."""
    claim_id = await _create_claim_for_denial(client, engine)

    resp = await client.post(
        "/v1/denials",
        json={
            "claim_id": claim_id,
            "denial_reason_code": "CO-4",
            "denial_reason_description": "The service is not covered under the patient's plan.",
            "denied_amount": 350.00,
            "payer_name": "Delta Dental",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert resp.status_code == 201
    return resp.json()["id"], claim_id


async def test_create_denial(client, engine):
    claim_id = await _create_claim_for_denial(client, engine)

    response = await client.post(
        "/v1/denials",
        json={
            "claim_id": claim_id,
            "denial_reason_code": "CO-4",
            "denial_reason_description": "The service is not covered under the patient's plan.",
            "denied_amount": 350.00,
            "payer_name": "Delta Dental",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["claim_id"] == claim_id
    assert data["denial_reason_code"] == "CO-4"
    assert data["denied_amount"] == 350.00
    assert data["payer_name"] == "Delta Dental"
    assert data["status"] == "denied"
    assert "id" in data


async def test_list_denials(client, engine):
    denial_id, claim_id = await _create_denial(client, engine)

    response = await client.get(
        "/v1/denials",
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    ids = [d["id"] for d in data]
    assert denial_id in ids


async def test_get_denial(client, engine):
    denial_id, claim_id = await _create_denial(client, engine)

    response = await client.get(
        f"/v1/denials/{denial_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == denial_id
    assert data["claim_id"] == claim_id
    assert data["denial_reason_code"] == "CO-4"
    assert data["status"] == "denied"


async def test_generate_appeal(client, engine):
    denial_id, _ = await _create_denial(client, engine)

    mock_appeal = AppealGenResponse(
        appeal_text="We formally appeal this denial...",
        case_law_citations=["Hughes v. Blue Cross (1989)"],
        key_arguments=["Clinical necessity documented"],
        recommended_attachments=["Radiograph"],
    )

    with patch("buckteeth.api.denials.AppealGenerator") as MockGen:
        MockGen.return_value.generate_appeal = AsyncMock(return_value=mock_appeal)

        response = await client.post(
            f"/v1/denials/{denial_id}/generate-appeal",
            json={
                "clinical_notes": "Patient has recurrent decay on tooth #14 requiring composite restoration.",
                "state": "CA",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["denial_id"] == denial_id
    assert data["appeal_text"] == "We formally appeal this denial..."
    assert data["generated_by"] == "ai"
    assert data["status"] == "draft"
    assert "id" in data


async def test_send_commissioner_letter(client, engine):
    denial_id, _ = await _create_denial(client, engine)

    mock_letter = CommLetterGenResponse(
        letter_text="Dear Commissioner...",
        commissioner_name="California Department of Insurance",
        commissioner_address="300 Capitol Mall, Sacramento, CA 95814",
        case_law_citations=["Hughes v. Blue Cross (1989)"],
        regulatory_citations=["CA Insurance Code § 10123.135"],
    )

    with patch("buckteeth.api.denials.CommissionerLetterGenerator") as MockGen:
        MockGen.return_value.generate = AsyncMock(return_value=mock_letter)

        response = await client.post(
            f"/v1/denials/{denial_id}/send-commissioner-letter",
            json={
                "patient_address": "123 Main St, Los Angeles, CA 90001",
                "provider_address": "456 Dental Ave, Los Angeles, CA 90002",
                "clinical_notes": "Patient has recurrent decay requiring treatment.",
                "state": "CA",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["denial_id"] == denial_id
    assert data["commissioner_name"] == "California Department of Insurance"
    assert data["letter_text"] == "Dear Commissioner..."
    assert data["mail_status"] == "created"
    assert data["mail_tracking_id"] is not None
    assert data["state"] == "CA"
    assert data["trigger_type"] == "manual"
    assert "id" in data
