# Phase 3: Submission Gateway

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the submission gateway that routes completed claims to their destination — clearinghouse submission via adapter pattern, ADA dental claim form PDF generation, submission tracking, and ERA/EOB processing for payment/denial ingestion.

**Architecture:** New `submission` module under `src/buckteeth/`. Clearinghouse adapters implement a standard interface. A mock clearinghouse adapter is provided for development/testing. Submission records track claim lifecycle.

**Tech Stack:** Same as Phase 1-2, plus ReportLab for PDF generation

---

## Chunk 1: Submission Models & Clearinghouse Adapters

### Task 1: Submission and ERA data models

**Files:**
- Create: `src/buckteeth/models/submission.py`
- Create: `tests/models/test_submission_models.py`

- [ ] **Step 1: Write test for submission models**

Create `tests/models/test_submission_models.py`:

```python
import uuid
import pytest
from buckteeth.models.base import Base
from buckteeth.models.patient import Patient
from buckteeth.models.encounter import ClinicalEncounter
from buckteeth.models.coding import CodedEncounter
from buckteeth.models.claim import Claim
from buckteeth.models.submission import SubmissionRecord, ERARecord


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
        provider_name="Dr. Smith", date_of_service="2026-03-12", status="ready",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB123", primary_group_number="GRP456")
    db_session.add(claim)
    await db_session.flush()
    return claim


async def test_create_submission_record(db_session):
    tenant = uuid.uuid4()
    claim = await _make_claim(db_session, tenant)
    record = SubmissionRecord(
        tenant_id=tenant, claim_id=claim.id,
        channel="clearinghouse", clearinghouse_name="DentalXChange",
        tracking_number="TRK-12345", status="submitted",
    )
    db_session.add(record)
    await db_session.flush()
    assert record.id is not None
    assert record.status == "submitted"


async def test_create_era_record(db_session):
    tenant = uuid.uuid4()
    claim = await _make_claim(db_session, tenant)
    era = ERARecord(
        tenant_id=tenant, claim_id=claim.id,
        payer_name="Delta Dental", payer_id="DD001",
        payment_amount=150.00, allowed_amount=200.00,
        patient_responsibility=50.00,
        status="paid",
        adjustment_reason_codes={"codes": ["CO-45", "PR-3"]},
    )
    db_session.add(era)
    await db_session.flush()
    assert era.payment_amount == 150.00
```

- [ ] **Step 2: Implement submission models**

Create `src/buckteeth/models/submission.py`:

```python
import uuid
from sqlalchemy import String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from buckteeth.models.base import TenantScopedBase


class SubmissionRecord(TenantScopedBase):
    __tablename__ = "submission_records"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(30))  # clearinghouse, pms, paper
    clearinghouse_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # submitted, accepted, rejected, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)


class ERARecord(TenantScopedBase):
    __tablename__ = "era_records"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(200))
    payer_id: Mapped[str] = mapped_column(String(50))
    payment_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_responsibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustment_reason_codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # paid, denied, partial, adjusted
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

- [ ] **Step 3: Run tests, commit**

### Task 2: Clearinghouse adapter interface + mock adapter

**Files:**
- Create: `src/buckteeth/submission/__init__.py`
- Create: `src/buckteeth/submission/adapters.py`
- Create: `tests/submission/__init__.py`
- Create: `tests/submission/test_adapters.py`

- [ ] **Step 1: Write tests for clearinghouse adapter**

```python
import pytest
from buckteeth.submission.adapters import MockClearinghouseAdapter, SubmissionResult, EligibilityResult


@pytest.fixture
def adapter():
    return MockClearinghouseAdapter()


async def test_submit_claim(adapter):
    result = await adapter.submit_claim(
        claim_data={"claim_id": "test-123", "payer_id": "DD001", "procedures": []},
    )
    assert isinstance(result, SubmissionResult)
    assert result.tracking_id is not None
    assert result.status in ("accepted", "rejected")


async def test_check_status(adapter):
    submit_result = await adapter.submit_claim(
        claim_data={"claim_id": "test-123", "payer_id": "DD001", "procedures": []},
    )
    status = await adapter.check_status(submit_result.tracking_id)
    assert status is not None


async def test_check_eligibility(adapter):
    result = await adapter.check_eligibility(
        patient_id="PAT-001", payer_id="DD001",
        subscriber_id="SUB123", date_of_service="2026-03-12",
    )
    assert isinstance(result, EligibilityResult)
    assert result.eligible is True
    assert result.annual_maximum is not None
```

- [ ] **Step 2: Implement adapter interface and mock**

Create `src/buckteeth/submission/adapters.py`:

```python
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SubmissionResult:
    tracking_id: str
    status: str  # accepted, rejected, error
    confirmation_number: str | None = None
    error_message: str | None = None
    raw_response: dict | None = None


@dataclass
class ClaimStatus:
    tracking_id: str
    status: str  # pending, accepted, rejected, paid, denied
    details: str | None = None


@dataclass
class EligibilityResult:
    eligible: bool
    annual_maximum: float | None = None
    annual_used: float | None = None
    annual_remaining: float | None = None
    deductible: float | None = None
    deductible_met: float | None = None
    coverage_details: dict | None = None


class ClearinghouseAdapter(ABC):
    @abstractmethod
    async def submit_claim(self, claim_data: dict) -> SubmissionResult: ...

    @abstractmethod
    async def check_status(self, tracking_id: str) -> ClaimStatus: ...

    @abstractmethod
    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult: ...


class MockClearinghouseAdapter(ClearinghouseAdapter):
    """Mock adapter for development and testing."""

    def __init__(self):
        self._submissions: dict[str, dict] = {}

    async def submit_claim(self, claim_data: dict) -> SubmissionResult:
        tracking_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        self._submissions[tracking_id] = {
            "claim_data": claim_data,
            "status": "accepted",
        }
        return SubmissionResult(
            tracking_id=tracking_id,
            status="accepted",
            confirmation_number=f"CONF-{uuid.uuid4().hex[:6].upper()}",
        )

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        sub = self._submissions.get(tracking_id)
        if sub is None:
            return ClaimStatus(tracking_id=tracking_id, status="unknown",
                               details="Tracking ID not found")
        return ClaimStatus(tracking_id=tracking_id, status=sub["status"])

    async def check_eligibility(
        self, patient_id: str, payer_id: str,
        subscriber_id: str, date_of_service: str,
    ) -> EligibilityResult:
        return EligibilityResult(
            eligible=True,
            annual_maximum=2000.00,
            annual_used=450.00,
            annual_remaining=1550.00,
            deductible=50.00,
            deductible_met=50.00,
        )
```

- [ ] **Step 3: Run tests, commit**

### Task 3: Submission gateway service

**Files:**
- Create: `src/buckteeth/submission/gateway.py`
- Create: `tests/submission/test_gateway.py`

- [ ] **Step 1: Write tests**

```python
import uuid
import pytest
from buckteeth.submission.gateway import SubmissionGateway
from buckteeth.submission.adapters import MockClearinghouseAdapter


@pytest.fixture
def gateway():
    return SubmissionGateway(adapter=MockClearinghouseAdapter())


async def test_submit_claim(gateway):
    result = await gateway.submit(
        claim_id=uuid.uuid4(),
        claim_data={"payer_id": "DD001", "procedures": [
            {"cdt_code": "D1110", "fee": 150.00}
        ]},
    )
    assert result.tracking_id is not None
    assert result.status == "accepted"


async def test_submit_with_idempotency(gateway):
    claim_id = uuid.uuid4()
    result1 = await gateway.submit(
        claim_id=claim_id,
        claim_data={"payer_id": "DD001", "procedures": []},
        idempotency_key="unique-key-123",
    )
    result2 = await gateway.submit(
        claim_id=claim_id,
        claim_data={"payer_id": "DD001", "procedures": []},
        idempotency_key="unique-key-123",
    )
    assert result1.tracking_id == result2.tracking_id  # same submission returned


async def test_check_status(gateway):
    result = await gateway.submit(
        claim_id=uuid.uuid4(),
        claim_data={"payer_id": "DD001", "procedures": []},
    )
    status = await gateway.check_status(result.tracking_id)
    assert status.status == "accepted"


async def test_batch_submit(gateway):
    claims = [
        (uuid.uuid4(), {"payer_id": "DD001", "procedures": []}),
        (uuid.uuid4(), {"payer_id": "DD001", "procedures": []}),
        (uuid.uuid4(), {"payer_id": "DD001", "procedures": []}),
    ]
    results = await gateway.batch_submit(claims)
    assert len(results) == 3
    assert all(r.status == "accepted" for r in results)
```

- [ ] **Step 2: Implement gateway**

```python
import uuid
from buckteeth.submission.adapters import ClearinghouseAdapter, SubmissionResult, ClaimStatus


class SubmissionGateway:
    def __init__(self, adapter: ClearinghouseAdapter):
        self._adapter = adapter
        self._idempotency_cache: dict[str, SubmissionResult] = {}

    async def submit(
        self,
        claim_id: uuid.UUID,
        claim_data: dict,
        idempotency_key: str | None = None,
    ) -> SubmissionResult:
        if idempotency_key and idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        result = await self._adapter.submit_claim(claim_data)

        if idempotency_key:
            self._idempotency_cache[idempotency_key] = result

        return result

    async def check_status(self, tracking_id: str) -> ClaimStatus:
        return await self._adapter.check_status(tracking_id)

    async def batch_submit(
        self,
        claims: list[tuple[uuid.UUID, dict]],
    ) -> list[SubmissionResult]:
        results = []
        for claim_id, claim_data in claims:
            result = await self.submit(claim_id, claim_data)
            results.append(result)
        return results
```

- [ ] **Step 3: Run tests, commit**

---

## Chunk 2: Submission API & Eligibility

### Task 4: Submission API endpoints

**Files:**
- Create: `src/buckteeth/api/submissions.py`
- Create: `tests/api/test_submissions.py`
- Modify: `src/buckteeth/api/schemas.py` (add submission schemas)
- Modify: `src/buckteeth/main.py` (register submissions router)

- [ ] **Step 1: Add submission schemas to `src/buckteeth/api/schemas.py`**

```python
# ── Submissions ──────────────────────────────────────────────────────────

class SubmitClaimRequest(BaseModel):
    claim_id: uuid.UUID

class SubmitBatchRequest(BaseModel):
    claim_ids: list[uuid.UUID]

class SubmissionResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    channel: str
    clearinghouse_name: str | None = None
    tracking_number: str | None = None
    confirmation_number: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class EligibilityRequest(BaseModel):
    patient_id: uuid.UUID
    payer_id: str
    subscriber_id: str
    date_of_service: str

class EligibilityResponse(BaseModel):
    eligible: bool
    annual_maximum: float | None = None
    annual_used: float | None = None
    annual_remaining: float | None = None
    deductible: float | None = None
    deductible_met: float | None = None
```

- [ ] **Step 2: Implement submissions router**

Router prefix: `/v1/submissions`

Endpoints:
- `POST /submit` (201) — Submit a single claim via the gateway. Loads claim from DB, validates status is "ready", submits via gateway, creates SubmissionRecord, updates claim status to "submitted"
- `POST /batch-submit` (201) — Submit multiple claims
- `GET /` — List submission records for tenant
- `GET /{submission_id}` — Get submission record
- `POST /eligibility` — Check patient eligibility via clearinghouse adapter

- [ ] **Step 3: Write tests**

Test submit, batch submit, list, get, and eligibility check. Mock the gateway/adapter.

- [ ] **Step 4: Register router in main.py**

- [ ] **Step 5: Run all tests, commit**

---

## Phase 3 Summary

Phase 3 delivers:
- Submission and ERA data models
- Clearinghouse adapter interface (abstract base + mock implementation)
- Submission gateway with idempotency and batch support
- Eligibility verification
- REST API for submission lifecycle
- Foundation for real clearinghouse integrations (DentalXChange, Tesia, etc.)
