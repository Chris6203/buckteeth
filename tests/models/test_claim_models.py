import uuid

import pytest

from buckteeth.models.base import Base
from buckteeth.models.patient import Patient
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure
from buckteeth.models.claim import Claim, ClaimProcedure, ClaimNarrative


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
async def prerequisite_objects(db_session, tenant_id):
    """Create the chain: Patient -> ClinicalEncounter -> ClinicalProcedure -> CodedEncounter -> CodedProcedure."""
    patient = Patient(
        tenant_id=tenant_id,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1990-01-15",
        gender="female",
    )
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        raw_input_type="text",
        status="completed",
    )
    db_session.add(encounter)
    await db_session.flush()

    clinical_proc = ClinicalProcedure(
        tenant_id=tenant_id,
        encounter_id=encounter.id,
        description="Crown on tooth #30",
        tooth_numbers=[30],
    )
    db_session.add(clinical_proc)
    await db_session.flush()

    coded_encounter = CodedEncounter(
        tenant_id=tenant_id,
        encounter_id=encounter.id,
        review_status="approved",
    )
    db_session.add(coded_encounter)
    await db_session.flush()

    coded_proc = CodedProcedure(
        tenant_id=tenant_id,
        coded_encounter_id=coded_encounter.id,
        clinical_procedure_id=clinical_proc.id,
        cdt_code="D2740",
        cdt_description="Crown - porcelain/ceramic substrate",
        tooth_number="30",
        confidence_score=95,
        ai_reasoning="Full coverage crown on molar #30",
    )
    db_session.add(coded_proc)
    await db_session.flush()

    return {
        "patient": patient,
        "encounter": encounter,
        "clinical_proc": clinical_proc,
        "coded_encounter": coded_encounter,
        "coded_proc": coded_proc,
    }


async def test_create_claim_with_required_fields(db_session, tenant_id, prerequisite_objects):
    objs = prerequisite_objects
    claim = Claim(
        tenant_id=tenant_id,
        coded_encounter_id=objs["coded_encounter"].id,
        patient_id=objs["patient"].id,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        status="draft",
        primary_payer_name="Delta Dental",
        primary_payer_id="DD001",
        primary_subscriber_id="SUB123456",
        primary_group_number="GRP789",
    )
    db_session.add(claim)
    await db_session.flush()

    assert claim.id is not None
    assert claim.tenant_id == tenant_id
    assert claim.coded_encounter_id == objs["coded_encounter"].id
    assert claim.patient_id == objs["patient"].id
    assert claim.provider_name == "Dr. Smith"
    assert claim.date_of_service == "2026-03-12"
    assert claim.status == "draft"
    assert claim.primary_payer_name == "Delta Dental"
    assert claim.primary_payer_id == "DD001"
    assert claim.preauth_required is False
    assert claim.secondary_payer_name is None
    assert claim.total_fee_submitted is None
    assert claim.created_at is not None


async def test_create_claim_with_procedures(db_session, tenant_id, prerequisite_objects):
    objs = prerequisite_objects
    claim = Claim(
        tenant_id=tenant_id,
        coded_encounter_id=objs["coded_encounter"].id,
        patient_id=objs["patient"].id,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        primary_payer_name="Delta Dental",
        primary_payer_id="DD001",
        primary_subscriber_id="SUB123456",
        primary_group_number="GRP789",
        total_fee_submitted=1200.00,
    )
    db_session.add(claim)
    await db_session.flush()

    procedure = ClaimProcedure(
        tenant_id=tenant_id,
        claim_id=claim.id,
        coded_procedure_id=objs["coded_proc"].id,
        cdt_code="D2740",
        cdt_description="Crown - porcelain/ceramic substrate",
        tooth_number="30",
        fee_submitted=1200.00,
    )
    db_session.add(procedure)
    await db_session.flush()

    assert procedure.id is not None
    assert procedure.claim_id == claim.id
    assert procedure.cdt_code == "D2740"
    assert procedure.fee_submitted == 1200.00

    await db_session.refresh(claim, ["procedures"])
    assert len(claim.procedures) == 1
    assert claim.procedures[0].cdt_code == "D2740"


async def test_create_claim_with_narrative(db_session, tenant_id, prerequisite_objects):
    objs = prerequisite_objects
    claim = Claim(
        tenant_id=tenant_id,
        coded_encounter_id=objs["coded_encounter"].id,
        patient_id=objs["patient"].id,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        primary_payer_name="Delta Dental",
        primary_payer_id="DD001",
        primary_subscriber_id="SUB123456",
        primary_group_number="GRP789",
    )
    db_session.add(claim)
    await db_session.flush()

    narrative = ClaimNarrative(
        tenant_id=tenant_id,
        claim_id=claim.id,
        cdt_code="D2740",
        narrative_text="Patient requires full coverage crown on tooth #30 due to extensive decay.",
        generated_by="ai",
        payer_tailored=True,
    )
    db_session.add(narrative)
    await db_session.flush()

    assert narrative.id is not None
    assert narrative.claim_id == claim.id
    assert narrative.generated_by == "ai"
    assert narrative.payer_tailored is True

    await db_session.refresh(claim, ["narratives"])
    assert len(claim.narratives) == 1
    assert claim.narratives[0].narrative_text.startswith("Patient requires")
