import uuid

import pytest

from buckteeth.models.base import Base
from buckteeth.models.patient import Patient
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure
from buckteeth.models.claim import Claim
from buckteeth.models.submission import SubmissionRecord, ERARecord


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
async def claim_chain(db_session, tenant_id):
    """Create the chain: Patient -> Encounter -> CodedEncounter -> Claim."""
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

    claim = Claim(
        tenant_id=tenant_id,
        coded_encounter_id=coded_encounter.id,
        patient_id=patient.id,
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

    return {"patient": patient, "claim": claim}


async def test_create_submission_record(db_session, tenant_id, claim_chain):
    claim = claim_chain["claim"]
    submission = SubmissionRecord(
        tenant_id=tenant_id,
        claim_id=claim.id,
        channel="clearinghouse",
        clearinghouse_name="DentalXChange",
        tracking_number="TRK-001",
        confirmation_number="CONF-001",
        status="submitted",
        idempotency_key="idem-key-001",
    )
    db_session.add(submission)
    await db_session.flush()

    assert submission.id is not None
    assert submission.tenant_id == tenant_id
    assert submission.claim_id == claim.id
    assert submission.channel == "clearinghouse"
    assert submission.clearinghouse_name == "DentalXChange"
    assert submission.tracking_number == "TRK-001"
    assert submission.confirmation_number == "CONF-001"
    assert submission.status == "submitted"
    assert submission.idempotency_key == "idem-key-001"
    assert submission.error_message is None
    assert submission.response_data is None
    assert submission.created_at is not None


async def test_create_era_record(db_session, tenant_id, claim_chain):
    claim = claim_chain["claim"]
    era = ERARecord(
        tenant_id=tenant_id,
        claim_id=claim.id,
        payer_name="Delta Dental",
        payer_id="DD001",
        payment_amount=950.00,
        allowed_amount=1100.00,
        patient_responsibility=150.00,
        adjustment_reason_codes={"CO-45": "Charges exceed fee schedule"},
        status="paid",
        check_number="CHK-99887",
    )
    db_session.add(era)
    await db_session.flush()

    assert era.id is not None
    assert era.tenant_id == tenant_id
    assert era.claim_id == claim.id
    assert era.payer_name == "Delta Dental"
    assert era.payer_id == "DD001"
    assert era.payment_amount == 950.00
    assert era.allowed_amount == 1100.00
    assert era.patient_responsibility == 150.00
    assert era.adjustment_reason_codes == {"CO-45": "Charges exceed fee schedule"}
    assert era.status == "paid"
    assert era.denial_reason is None
    assert era.check_number == "CHK-99887"
    assert era.created_at is not None
