import uuid
import pytest
from buckteeth.models.base import Base
from buckteeth.models.patient import Patient
from buckteeth.models.encounter import ClinicalEncounter
from buckteeth.models.coding import CodedEncounter
from buckteeth.models.claim import Claim
from buckteeth.models.denial import DenialRecord, AppealDocument, CommissionerLetter


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _make_claim(db_session, tenant):
    patient = Patient(tenant_id=tenant, first_name="Jane", last_name="Doe",
                      date_of_birth="1990-01-15", gender="F")
    db_session.add(patient)
    await db_session.flush()
    encounter = ClinicalEncounter(tenant_id=tenant, patient_id=patient.id,
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        raw_notes="test", raw_input_type="text")
    db_session.add(encounter)
    await db_session.flush()
    coded = CodedEncounter(tenant_id=tenant, encounter_id=encounter.id)
    db_session.add(coded)
    await db_session.flush()
    claim = Claim(tenant_id=tenant, coded_encounter_id=coded.id, patient_id=patient.id,
        provider_name="Dr. Smith", date_of_service="2026-03-12", status="denied",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB123", primary_group_number="GRP456")
    db_session.add(claim)
    await db_session.flush()
    return claim, patient


async def test_create_denial_record(db_session):
    tenant = uuid.uuid4()
    claim, _ = await _make_claim(db_session, tenant)
    denial = DenialRecord(
        tenant_id=tenant, claim_id=claim.id,
        denial_reason_code="CO-45",
        denial_reason_description="Charges exceed your contracted/legislated fee arrangement",
        denied_amount=150.00,
        payer_name="Delta Dental",
        status="denied",
    )
    db_session.add(denial)
    await db_session.flush()
    assert denial.id is not None


async def test_create_appeal_document(db_session):
    tenant = uuid.uuid4()
    claim, _ = await _make_claim(db_session, tenant)
    denial = DenialRecord(
        tenant_id=tenant, claim_id=claim.id,
        denial_reason_code="CO-45",
        denial_reason_description="Charges exceed fee arrangement",
        denied_amount=150.00, payer_name="Delta Dental", status="denied",
    )
    db_session.add(denial)
    await db_session.flush()

    appeal = AppealDocument(
        tenant_id=tenant, denial_id=denial.id,
        appeal_text="We respectfully appeal this denial...",
        case_law_citations={"citations": ["Smith v. Delta Dental, 2019"]},
        generated_by="ai", status="draft",
    )
    db_session.add(appeal)
    await db_session.flush()
    assert appeal.denial_id == denial.id


async def test_create_commissioner_letter(db_session):
    tenant = uuid.uuid4()
    claim, patient = await _make_claim(db_session, tenant)
    denial = DenialRecord(
        tenant_id=tenant, claim_id=claim.id,
        denial_reason_code="CO-45",
        denial_reason_description="Fee arrangement",
        denied_amount=150.00, payer_name="Delta Dental", status="denied",
    )
    db_session.add(denial)
    await db_session.flush()

    letter = CommissionerLetter(
        tenant_id=tenant, denial_id=denial.id,
        patient_id=patient.id,
        state="CA",
        commissioner_name="California Department of Insurance",
        commissioner_address="300 Capitol Mall, Sacramento, CA 95814",
        letter_text="Dear Commissioner...",
        case_law_citations={"citations": ["Smith v. Delta Dental, 2019"]},
        mail_status="pending",
        trigger_type="manual",
    )
    db_session.add(letter)
    await db_session.flush()
    assert letter.mail_status == "pending"
