import uuid

import pytest

from buckteeth.models.base import Base
from buckteeth.models.patient import Patient, InsurancePlan
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure
from buckteeth.models.audit import AuditLog


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_create_patient(db_session):
    tenant_id = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant_id,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1990-01-15",
        gender="female",
    )
    db_session.add(patient)
    await db_session.flush()

    assert patient.id is not None
    assert patient.tenant_id == tenant_id
    assert patient.first_name == "Jane"
    assert patient.last_name == "Doe"
    assert patient.date_of_birth == "1990-01-15"
    assert patient.gender == "female"
    assert patient.created_at is not None


async def test_patient_with_insurance_plan(db_session):
    tenant_id = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant_id,
        first_name="John",
        last_name="Smith",
        date_of_birth="1985-06-20",
        gender="male",
    )
    db_session.add(patient)
    await db_session.flush()

    plan = InsurancePlan(
        tenant_id=tenant_id,
        patient_id=patient.id,
        payer_name="Delta Dental",
        payer_id="DD001",
        subscriber_id="SUB123456",
        group_number="GRP789",
        plan_type="primary",
    )
    db_session.add(plan)
    await db_session.flush()

    assert plan.id is not None
    assert plan.patient_id == patient.id
    assert plan.payer_name == "Delta Dental"
    assert plan.plan_type == "primary"

    await db_session.refresh(patient, ["insurance_plans"])
    assert len(patient.insurance_plans) == 1
    assert patient.insurance_plans[0].payer_name == "Delta Dental"


async def test_clinical_encounter_with_procedures(db_session):
    tenant_id = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant_id,
        first_name="Alice",
        last_name="Brown",
        date_of_birth="1978-03-10",
        gender="female",
    )
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_name="Dr. Williams",
        date_of_service="2026-03-12",
        raw_notes="Patient presents with cavity on tooth #14",
        raw_input_type="text",
        status="pending",
    )
    db_session.add(encounter)
    await db_session.flush()

    procedure = ClinicalProcedure(
        tenant_id=tenant_id,
        encounter_id=encounter.id,
        description="Composite filling on tooth #14, MO surfaces",
        tooth_numbers=[14],
        surfaces=["M", "O"],
        quadrant="upper-left",
        diagnosis="Dental caries",
    )
    db_session.add(procedure)
    await db_session.flush()

    assert encounter.id is not None
    assert encounter.status == "pending"
    assert procedure.encounter_id == encounter.id

    await db_session.refresh(encounter, ["procedures"])
    assert len(encounter.procedures) == 1
    assert encounter.procedures[0].description.startswith("Composite filling")


async def test_coded_encounter_with_coded_procedures(db_session):
    tenant_id = uuid.uuid4()

    # Create prerequisite objects
    patient = Patient(
        tenant_id=tenant_id,
        first_name="Bob",
        last_name="Jones",
        date_of_birth="1995-11-05",
        gender="male",
    )
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_name="Dr. Lee",
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
        review_status="pending",
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
        confidence_score=92,
        ai_reasoning="Clinical notes indicate full coverage crown on molar #30",
        flags={"bundling_check": False},
        icd10_codes=["K02.9"],
    )
    db_session.add(coded_proc)
    await db_session.flush()

    assert coded_encounter.id is not None
    assert coded_proc.cdt_code == "D2740"
    assert coded_proc.confidence_score == 92

    await db_session.refresh(coded_encounter, ["coded_procedures"])
    assert len(coded_encounter.coded_procedures) == 1
    assert coded_encounter.coded_procedures[0].cdt_code == "D2740"


async def test_audit_log(db_session):
    tenant_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    log = AuditLog(
        tenant_id=tenant_id,
        action="code_override",
        entity_type="coded_procedure",
        entity_id=entity_id,
        user_id="user@example.com",
        details={"old_code": "D2740", "new_code": "D2750", "reason": "Material mismatch"},
    )
    db_session.add(log)
    await db_session.flush()

    assert log.id is not None
    assert log.action == "code_override"
    assert log.entity_type == "coded_procedure"
    assert log.entity_id == entity_id
    assert log.details["old_code"] == "D2740"
    assert log.created_at is not None
