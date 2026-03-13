import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.claims.schemas import ClaimDetail, ClaimProcedureDetail, NarrativeResponse
from buckteeth.coding.schemas import CodeSuggestion, CodingResult
from buckteeth.database import get_db
from buckteeth.denials.risk_scorer import RiskAssessment
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
        procedures=[ParsedProcedure(
            description="MOD composite restoration",
            tooth_numbers=[14], surfaces=["M", "O", "D"],
            quadrant="upper right", diagnosis="recurrent decay",
        )],
        notes="Routine visit",
    )


def _mock_coding_result():
    return CodingResult(
        suggestions=[CodeSuggestion(
            cdt_code="D2393",
            cdt_description="Resin-based composite - three surfaces, posterior",
            tooth_number="14", surfaces="MOD", quadrant="upper right",
            confidence_score=95,
            ai_reasoning="Three-surface posterior composite",
            flags=[], icd10_codes=["K02.9"],
        )],
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
        procedures=[ClaimProcedureDetail(
            cdt_code="D2393",
            cdt_description="Resin-based composite - three surfaces, posterior",
            tooth_number="14", surfaces="MOD", quadrant="upper right",
            narrative=NarrativeResponse(
                cdt_code="D2393",
                narrative_text="Patient presented with recurrent decay.",
                payer_tailored=True,
            ),
        )],
        narratives=[NarrativeResponse(
            cdt_code="D2393",
            narrative_text="Patient presented with recurrent decay.",
            payer_tailored=True,
        )],
        preauth_required=False,
        procedure_count=1, has_narratives=True, has_preauth=False,
    )


async def _create_claim(client, engine):
    from buckteeth.models.patient import InsurancePlan

    patient_resp = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe",
              "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = patient_resp.json()["id"]

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        plan = InsurancePlan(
            tenant_id=uuid.UUID(TENANT_ID),
            patient_id=uuid.UUID(patient_id),
            payer_name="Delta Dental", payer_id="DELTA-001",
            subscriber_id="SUB-001", group_number="GRP-001",
            plan_type="primary",
        )
        session.add(plan)
        await session.commit()

    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        MockParser.return_value.parse = AsyncMock(return_value=_mock_parsed())
        enc_resp = await client.post(
            "/v1/encounters/from-notes",
            json={"patient_id": patient_id, "provider_name": "Dr. Smith",
                  "date_of_service": "2026-03-12",
                  "notes": "MOD composite on #14"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    encounter_id = enc_resp.json()["id"]

    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        MockEngine.return_value.code_encounter = AsyncMock(
            return_value=_mock_coding_result())
        code_resp = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    coded_enc_id = code_resp.json()["id"]

    with patch("buckteeth.api.claims.ClaimBuilder") as MockBuilder:
        MockBuilder.return_value.build = AsyncMock(
            return_value=_mock_claim_detail())
        claim_resp = await client.post(
            "/v1/claims",
            json={"coded_encounter_id": coded_enc_id},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    return claim_resp.json()["id"]


async def test_assess_denial_risk(client, engine):
    claim_id = await _create_claim(client, engine)

    mock_assessment = RiskAssessment(
        risk_score=25,
        risk_level="low",
        risk_factors=[],
        recommendations=["Claim looks routine, proceed with submission"],
    )

    with patch("buckteeth.api.claims.DenialRiskScorer") as MockScorer:
        MockScorer.return_value.assess = AsyncMock(return_value=mock_assessment)

        response = await client.post(
            f"/v1/claims/{claim_id}/assess-risk",
            json={"patient_age": 35},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] == 25
    assert data["risk_level"] == "low"
    assert isinstance(data["risk_factors"], list)
    assert isinstance(data["recommendations"], list)


async def test_assess_risk_claim_not_found(client):
    response = await client.post(
        f"/v1/claims/{uuid.uuid4()}/assess-risk",
        json={"patient_age": 35},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404


async def test_download_claim_pdf(client, engine):
    claim_id = await _create_claim(client, engine)

    response = await client.get(
        f"/v1/claims/{claim_id}/pdf",
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
