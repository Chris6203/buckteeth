# Phase 2: Claim Builder & Narrative Generation

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the claim builder module that assembles complete insurance claims from coded encounters, generates clinical narratives via Claude, manages attachments, handles pre-authorizations, and supports coordination of benefits. Add API endpoints for claim lifecycle.

**Architecture:** New `claims` module under `src/buckteeth/`. Claim and Narrative models added to the existing models package. Claude-powered narrative generation follows the same RAG pattern as the coding engine.

**Tech Stack:** Same as Phase 1 — Python 3.12, FastAPI, SQLAlchemy 2.0, Anthropic SDK, Pydantic v2

---

## Chunk 1: Claim Data Model & Narrative Generator

### File Structure (Chunk 1)

```
src/buckteeth/
├── models/
│   └── claim.py               # Claim, ClaimProcedure, Narrative, Attachment models
├── claims/
│   ├── __init__.py
│   ├── schemas.py             # Pydantic schemas for claims
│   ├── narrative.py           # Claude-powered narrative generator
│   └── builder.py             # Claim builder orchestrator
tests/
├── models/
│   └── test_claim_models.py
├── claims/
│   ├── __init__.py
│   ├── test_narrative.py
│   └── test_builder.py
```

### Task 1: Claim data models

**Files:**
- Create: `src/buckteeth/models/claim.py`
- Create: `tests/models/test_claim_models.py`

- [ ] **Step 1: Write test for Claim models**

Create `tests/models/test_claim_models.py`:

```python
import uuid
import pytest
from buckteeth.models.base import Base
from buckteeth.models.patient import Patient
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure
from buckteeth.models.claim import Claim, ClaimProcedure, ClaimNarrative, ClaimAttachment


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_create_claim(db_session):
    tenant = uuid.uuid4()
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

    claim = Claim(
        tenant_id=tenant, coded_encounter_id=coded.id, patient_id=patient.id,
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        status="draft",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB123", primary_group_number="GRP456",
    )
    db_session.add(claim)
    await db_session.flush()
    assert claim.id is not None
    assert claim.status == "draft"


async def test_claim_with_procedures(db_session):
    tenant = uuid.uuid4()
    patient = Patient(tenant_id=tenant, first_name="Jane", last_name="Doe",
                      date_of_birth="1990-01-15", gender="F")
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(tenant_id=tenant, patient_id=patient.id,
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        raw_notes="test", raw_input_type="text")
    db_session.add(encounter)
    await db_session.flush()

    proc = ClinicalProcedure(tenant_id=tenant, encounter_id=encounter.id,
        description="MOD composite", diagnosis="decay")
    db_session.add(proc)
    await db_session.flush()

    coded = CodedEncounter(tenant_id=tenant, encounter_id=encounter.id)
    db_session.add(coded)
    await db_session.flush()

    coded_proc = CodedProcedure(tenant_id=tenant, coded_encounter_id=coded.id,
        clinical_procedure_id=proc.id, cdt_code="D2393",
        cdt_description="Composite - three surfaces, posterior",
        confidence_score=95, ai_reasoning="MOD composite #14")
    db_session.add(coded_proc)
    await db_session.flush()

    claim = Claim(tenant_id=tenant, coded_encounter_id=coded.id,
        patient_id=patient.id, provider_name="Dr. Smith",
        date_of_service="2026-03-12", status="draft",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB123", primary_group_number="GRP456")
    db_session.add(claim)
    await db_session.flush()

    claim_proc = ClaimProcedure(
        tenant_id=tenant, claim_id=claim.id,
        coded_procedure_id=coded_proc.id,
        cdt_code="D2393", cdt_description="Composite - three surfaces, posterior",
        tooth_number="14", surfaces="MOD",
        fee_submitted=250.00,
    )
    db_session.add(claim_proc)
    await db_session.flush()
    assert claim_proc.claim_id == claim.id


async def test_claim_narrative(db_session):
    tenant = uuid.uuid4()
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

    claim = Claim(tenant_id=tenant, coded_encounter_id=coded.id,
        patient_id=patient.id, provider_name="Dr. Smith",
        date_of_service="2026-03-12", status="draft",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB123", primary_group_number="GRP456")
    db_session.add(claim)
    await db_session.flush()

    narrative = ClaimNarrative(
        tenant_id=tenant, claim_id=claim.id,
        cdt_code="D4341",
        narrative_text="Patient presents with generalized moderate periodontitis...",
        generated_by="ai",
    )
    db_session.add(narrative)
    await db_session.flush()
    assert narrative.claim_id == claim.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_claim_models.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement Claim models**

Create `src/buckteeth/models/claim.py`:

```python
import uuid
from sqlalchemy import String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from buckteeth.models.base import TenantScopedBase


class Claim(TenantScopedBase):
    __tablename__ = "claims"

    coded_encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coded_encounters.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(200))
    date_of_service: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # Status: draft, ready, submitted, accepted, denied, appealed, paid

    # Primary insurance
    primary_payer_name: Mapped[str] = mapped_column(String(200))
    primary_payer_id: Mapped[str] = mapped_column(String(50))
    primary_subscriber_id: Mapped[str] = mapped_column(String(100))
    primary_group_number: Mapped[str] = mapped_column(String(100))

    # Secondary insurance (optional)
    secondary_payer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secondary_payer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_subscriber_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Preauthorization
    preauth_required: Mapped[bool] = mapped_column(default=False)
    preauth_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preauth_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Fee totals
    total_fee_submitted: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_fee_allowed: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_fee_paid: Mapped[float | None] = mapped_column(Float, nullable=True)

    procedures: Mapped[list["ClaimProcedure"]] = relationship(back_populates="claim")
    narratives: Mapped[list["ClaimNarrative"]] = relationship(back_populates="claim")
    attachments: Mapped[list["ClaimAttachment"]] = relationship(back_populates="claim")


class ClaimProcedure(TenantScopedBase):
    __tablename__ = "claim_procedures"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    coded_procedure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coded_procedures.id"), nullable=False
    )
    cdt_code: Mapped[str] = mapped_column(String(10))
    cdt_description: Mapped[str] = mapped_column(Text)
    tooth_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    surfaces: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fee_submitted: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_allowed: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_paid: Mapped[float | None] = mapped_column(Float, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="procedures")


class ClaimNarrative(TenantScopedBase):
    __tablename__ = "claim_narratives"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    cdt_code: Mapped[str] = mapped_column(String(10))
    narrative_text: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[str] = mapped_column(String(20))  # ai, human
    payer_tailored: Mapped[bool] = mapped_column(default=False)

    claim: Mapped["Claim"] = relationship(back_populates="narratives")


class ClaimAttachment(TenantScopedBase):
    __tablename__ = "claim_attachments"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # xray, perio_chart, photo, document
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))  # S3 key
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="attachments")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/models/test_claim_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/models/claim.py tests/models/test_claim_models.py
git commit -m "feat: add Claim, ClaimProcedure, ClaimNarrative, ClaimAttachment models"
```

### Task 2: Claim and narrative schemas

**Files:**
- Create: `src/buckteeth/claims/__init__.py`
- Create: `src/buckteeth/claims/schemas.py`

- [ ] **Step 1: Create claim schemas**

Create `src/buckteeth/claims/__init__.py` (empty).

Create `src/buckteeth/claims/schemas.py`:

```python
import uuid
from pydantic import BaseModel


class NarrativeRequest(BaseModel):
    cdt_code: str
    procedure_description: str
    clinical_notes: str
    diagnosis: str | None = None
    tooth_number: str | None = None
    surfaces: str | None = None
    payer_name: str | None = None


class NarrativeResponse(BaseModel):
    cdt_code: str
    narrative_text: str
    payer_tailored: bool = False


class ClaimBuildRequest(BaseModel):
    coded_encounter_id: uuid.UUID
    primary_payer_id: str | None = None  # If None, uses patient's primary insurance


class ClaimProcedureDetail(BaseModel):
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    fee_submitted: float | None = None
    narrative: NarrativeResponse | None = None


class ClaimSummary(BaseModel):
    claim_id: uuid.UUID
    patient_name: str
    provider_name: str
    date_of_service: str
    status: str
    primary_payer_name: str
    total_fee: float | None = None
    procedure_count: int
    has_narratives: bool
    has_preauth: bool


class ClaimDetail(BaseModel):
    claim_id: uuid.UUID
    patient_name: str
    provider_name: str
    date_of_service: str
    status: str
    primary_payer_name: str
    primary_subscriber_id: str
    primary_group_number: str
    secondary_payer_name: str | None = None
    total_fee_submitted: float | None = None
    procedures: list[ClaimProcedureDetail]
    narratives: list[NarrativeResponse] = []
    preauth_required: bool = False
    preauth_number: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add src/buckteeth/claims/
git commit -m "feat: add claim and narrative Pydantic schemas"
```

### Task 3: Narrative generator (Claude-powered)

**Files:**
- Create: `src/buckteeth/claims/narrative.py`
- Create: `tests/claims/__init__.py`
- Create: `tests/claims/test_narrative.py`

- [ ] **Step 1: Write test for narrative generator**

Create `tests/claims/__init__.py` (empty) and `tests/claims/test_narrative.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.claims.narrative import NarrativeGenerator
from buckteeth.claims.schemas import NarrativeRequest, NarrativeResponse


@pytest.fixture
def generator():
    return NarrativeGenerator(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_generate_srp_narrative(generator):
    request = NarrativeRequest(
        cdt_code="D4341",
        procedure_description="Scaling and root planing - 4+ teeth, UR quadrant",
        clinical_notes="Generalized moderate periodontitis. Pocket depths 5-7mm UR quadrant. Bleeding on probing. Subgingular calculus present.",
        diagnosis="Generalized moderate periodontitis",
        payer_name="Delta Dental",
    )
    mock_narrative = '{"cdt_code": "D4341", "narrative_text": "Patient presents with generalized moderate periodontitis with probing depths of 5-7mm in the upper right quadrant. Bleeding on probing and subgingival calculus were noted. Scaling and root planing is necessary to remove bacterial deposits and promote tissue healing.", "payer_tailored": true}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_narrative)):
        result = await generator.generate(request)
        assert result.cdt_code == "D4341"
        assert "periodontitis" in result.narrative_text.lower()
        assert result.payer_tailored is True


async def test_generate_crown_narrative(generator):
    request = NarrativeRequest(
        cdt_code="D2740",
        procedure_description="Crown - porcelain/ceramic",
        clinical_notes="Tooth #30 has large MOD amalgam with recurrent decay and a mesial marginal ridge fracture.",
        diagnosis="Fractured tooth with recurrent decay",
        tooth_number="30",
    )
    mock_narrative = '{"cdt_code": "D2740", "narrative_text": "Tooth #30 presents with a large existing MOD amalgam restoration with recurrent decay at the margins and a fracture of the mesial marginal ridge. The remaining tooth structure is insufficient to support a direct restoration. A full coverage crown is recommended to restore function and prevent further breakdown.", "payer_tailored": false}'
    with patch.object(generator._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_narrative)):
        result = await generator.generate(request)
        assert result.cdt_code == "D2740"
        assert "crown" in result.narrative_text.lower()


async def test_needs_narrative_check(generator):
    assert generator.needs_narrative("D4341") is True  # SRP
    assert generator.needs_narrative("D2740") is True  # Crown
    assert generator.needs_narrative("D1110") is False  # Prophy
    assert generator.needs_narrative("D0120") is False  # Periodic eval
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/claims/test_narrative.py -v`
Expected: FAIL

- [ ] **Step 3: Implement narrative generator**

Create `src/buckteeth/claims/narrative.py`:

```python
import json
import anthropic
from buckteeth.claims.schemas import NarrativeRequest, NarrativeResponse
from buckteeth.knowledge.cdt_codes import CDTCodeRepository

SYSTEM_PROMPT = """You are a dental insurance narrative writer. Generate clinical narratives that justify medical necessity for dental procedures.

Your narratives should:
- Be concise but thorough (2-4 sentences)
- Use clinical terminology appropriate for insurance reviewers
- Reference specific clinical findings from the notes (pocket depths, fracture lines, decay extent)
- Explain why this specific procedure is necessary (not just what was done)
- If a payer name is provided, tailor language to what that payer typically accepts

Return JSON with:
- cdt_code: the CDT code
- narrative_text: the clinical narrative
- payer_tailored: true if tailored to a specific payer, false otherwise

Common narratives needed:
- SRP (D4341/D4342): Cite pocket depths, bleeding, calculus, bone loss
- Crowns (D2740/D2750): Cite fracture, extent of decay/existing restoration, remaining structure
- Core buildup (D2950): Cite insufficient remaining structure after caries removal
- Surgical extraction (D7210): Cite root morphology, bone removal needed
- Root canal (D3310/D3320/D3330): Cite pulpal involvement, periapical pathology
"""


class NarrativeGenerator:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._cdt_repo = CDTCodeRepository()

    def needs_narrative(self, cdt_code: str) -> bool:
        code_info = self._cdt_repo.lookup(cdt_code)
        if code_info is None:
            return False
        return code_info.narrative_required

    async def generate(self, request: NarrativeRequest) -> NarrativeResponse:
        prompt_parts = [
            f"CDT Code: {request.cdt_code}",
            f"Procedure: {request.procedure_description}",
            f"Clinical Notes: {request.clinical_notes}",
        ]
        if request.diagnosis:
            prompt_parts.append(f"Diagnosis: {request.diagnosis}")
        if request.tooth_number:
            prompt_parts.append(f"Tooth Number: {request.tooth_number}")
        if request.surfaces:
            prompt_parts.append(f"Surfaces: {request.surfaces}")
        if request.payer_name:
            prompt_parts.append(f"Payer: {request.payer_name} (tailor narrative for this payer)")

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
        return NarrativeResponse.model_validate(data)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/claims/test_narrative.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/claims/narrative.py tests/claims/
git commit -m "feat: add Claude-powered narrative generator for claim justification"
```

### Task 4: Claim builder orchestrator

**Files:**
- Create: `src/buckteeth/claims/builder.py`
- Create: `tests/claims/test_builder.py`

- [ ] **Step 1: Write test for claim builder**

Create `tests/claims/test_builder.py`:

```python
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.claims.builder import ClaimBuilder
from buckteeth.claims.schemas import NarrativeResponse, ClaimDetail
from buckteeth.coding.schemas import CodeSuggestion


@pytest.fixture
def builder():
    return ClaimBuilder(api_key="test-key")


async def test_build_claim_with_narrative(builder):
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D4341",
            cdt_description="SRP - 4+ teeth per quadrant",
            quadrant="UR",
            confidence_score=95,
            ai_reasoning="SRP needed",
            flags=["needs_narrative"],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    mock_narrative = NarrativeResponse(
        cdt_code="D4341",
        narrative_text="Patient presents with generalized moderate periodontitis...",
        payer_tailored=True,
    )
    with patch.object(builder._narrative_gen, "generate",
                      new_callable=AsyncMock, return_value=mock_narrative):
        result = await builder.build(
            coded_procedures=coded_procedures,
            patient_info=patient_info,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Pocket depths 5-7mm UR",
        )
        assert len(result.procedures) == 1
        assert result.procedures[0].cdt_code == "D4341"
        assert result.procedures[0].narrative is not None
        assert result.primary_payer_name == "Delta Dental"


async def test_build_claim_without_narrative(builder):
    coded_procedures = [
        CodeSuggestion(
            cdt_code="D1110",
            cdt_description="Prophylaxis - adult",
            confidence_score=99,
            ai_reasoning="Standard prophy",
            flags=[],
        ),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Routine cleaning",
    )
    assert len(result.procedures) == 1
    assert result.procedures[0].narrative is None


async def test_build_claim_multiple_procedures(builder):
    coded_procedures = [
        CodeSuggestion(cdt_code="D0120", cdt_description="Periodic eval",
            confidence_score=99, ai_reasoning="Routine exam", flags=[]),
        CodeSuggestion(cdt_code="D1110", cdt_description="Prophylaxis - adult",
            confidence_score=99, ai_reasoning="Cleaning", flags=[]),
        CodeSuggestion(cdt_code="D0274", cdt_description="Bitewings - four images",
            confidence_score=99, ai_reasoning="BWX", flags=[]),
    ]
    patient_info = {
        "name": "Jane Doe",
        "primary_payer_name": "Delta Dental",
        "primary_payer_id": "DD001",
        "primary_subscriber_id": "SUB123",
        "primary_group_number": "GRP456",
    }
    result = await builder.build(
        coded_procedures=coded_procedures,
        patient_info=patient_info,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        clinical_notes="Routine visit",
    )
    assert len(result.procedures) == 3
    assert result.procedure_count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/claims/test_builder.py -v`
Expected: FAIL

- [ ] **Step 3: Implement claim builder**

Create `src/buckteeth/claims/builder.py`:

```python
import uuid
from buckteeth.claims.narrative import NarrativeGenerator
from buckteeth.claims.schemas import (
    ClaimDetail, ClaimProcedureDetail, NarrativeRequest, NarrativeResponse,
)
from buckteeth.coding.schemas import CodeSuggestion


class ClaimBuilder:

    def __init__(self, api_key: str):
        self._narrative_gen = NarrativeGenerator(api_key=api_key)

    async def build(
        self,
        coded_procedures: list[CodeSuggestion],
        patient_info: dict,
        provider_name: str,
        date_of_service: str,
        clinical_notes: str,
    ) -> ClaimDetail:
        procedures: list[ClaimProcedureDetail] = []
        narratives: list[NarrativeResponse] = []

        for proc in coded_procedures:
            narrative = None
            if "needs_narrative" in proc.flags:
                narrative_req = NarrativeRequest(
                    cdt_code=proc.cdt_code,
                    procedure_description=proc.cdt_description,
                    clinical_notes=clinical_notes,
                    diagnosis=None,
                    tooth_number=proc.tooth_number,
                    surfaces=proc.surfaces,
                    payer_name=patient_info.get("primary_payer_name"),
                )
                narrative = await self._narrative_gen.generate(narrative_req)
                narratives.append(narrative)

            procedures.append(ClaimProcedureDetail(
                cdt_code=proc.cdt_code,
                cdt_description=proc.cdt_description,
                tooth_number=proc.tooth_number,
                surfaces=proc.surfaces,
                quadrant=proc.quadrant,
                narrative=narrative,
            ))

        total_fee = sum(p.fee_submitted or 0 for p in procedures) or None

        return ClaimDetail(
            claim_id=uuid.uuid4(),  # temporary ID until persisted
            patient_name=patient_info["name"],
            provider_name=provider_name,
            date_of_service=date_of_service,
            status="draft",
            primary_payer_name=patient_info["primary_payer_name"],
            primary_subscriber_id=patient_info["primary_subscriber_id"],
            primary_group_number=patient_info["primary_group_number"],
            secondary_payer_name=patient_info.get("secondary_payer_name"),
            total_fee_submitted=total_fee,
            procedures=procedures,
            narratives=narratives,
            preauth_required=any(
                self._narrative_gen.needs_narrative(p.cdt_code)
                and p.cdt_code in ("D2740", "D2750", "D5110", "D5120")
                for p in coded_procedures
            ),
            procedure_count=len(procedures),
            has_narratives=len(narratives) > 0,
            has_preauth=False,
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/claims/test_builder.py -v`
Expected: PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/claims/builder.py tests/claims/test_builder.py
git commit -m "feat: add claim builder orchestrator with narrative integration"
```

---

## Chunk 2: Claim API Endpoints

### File Structure (Chunk 2)

```
src/buckteeth/
├── api/
│   └── claims.py              # Claim lifecycle endpoints
tests/
├── api/
│   └── test_claims.py
```

### Task 5: Claim API endpoints

**Files:**
- Create: `src/buckteeth/api/claims.py`
- Create: `tests/api/test_claims.py`
- Modify: `src/buckteeth/main.py` (add claims router)
- Modify: `src/buckteeth/api/schemas.py` (add claim schemas)

- [ ] **Step 1: Add claim API schemas to `src/buckteeth/api/schemas.py`**

Append to the existing schemas file:

```python
# ── Claims ───────────────────────────────────────────────────────────────

class ClaimCreateRequest(BaseModel):
    coded_encounter_id: uuid.UUID

class ClaimNarrativeResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    narrative_text: str
    generated_by: str
    payer_tailored: bool = False
    model_config = {"from_attributes": True}

class ClaimProcedureResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    fee_submitted: float | None = None
    model_config = {"from_attributes": True}

class ClaimResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    coded_encounter_id: uuid.UUID
    provider_name: str
    date_of_service: str
    status: str
    primary_payer_name: str
    primary_payer_id: str
    primary_subscriber_id: str
    primary_group_number: str
    secondary_payer_name: str | None = None
    preauth_required: bool = False
    total_fee_submitted: float | None = None
    procedures: list[ClaimProcedureResponse] = []
    narratives: list[ClaimNarrativeResponse] = []
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class ClaimStatusUpdate(BaseModel):
    status: str  # ready, submitted, etc.
```

- [ ] **Step 2: Implement claims API router**

Create `src/buckteeth/api/claims.py`:

Router with prefix `/v1/claims`:
- `POST /` (201) — Build a claim from a coded encounter. Loads the coded encounter, patient's insurance, runs the ClaimBuilder (with narrative generation for flagged procedures), persists the Claim + ClaimProcedures + ClaimNarratives to DB.
- `GET /` — List claims for tenant (paginated, filterable by status)
- `GET /{claim_id}` — Get claim with procedures and narratives
- `PUT /{claim_id}/status` — Update claim status

The POST endpoint should:
1. Load CodedEncounter with coded_procedures
2. Load the ClinicalEncounter to get raw_notes and patient_id
3. Load Patient with insurance_plans to get payer info
4. Run ClaimBuilder.build() to generate the claim with narratives
5. Persist Claim, ClaimProcedure, ClaimNarrative records
6. Return the full claim

- [ ] **Step 3: Write tests for claims API**

Create `tests/api/test_claims.py` with tests for:
- Creating a claim from a coded encounter (mock narrative generator)
- Listing claims
- Getting a claim by ID
- Updating claim status

Use the same test fixture pattern as other API tests (override get_db, use test SQLite).

- [ ] **Step 4: Register claims router in main.py**

Add to `src/buckteeth/main.py`:
```python
from buckteeth.api.claims import router as claims_router
app.include_router(claims_router)
```

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/api/claims.py src/buckteeth/api/schemas.py src/buckteeth/main.py tests/api/test_claims.py
git commit -m "feat: add claim lifecycle API with narrative generation"
```

---

## Phase 2 Summary

Phase 2 delivers:
- Claim data models (Claim, ClaimProcedure, ClaimNarrative, ClaimAttachment)
- Claude-powered narrative generator for procedures requiring medical necessity justification
- Claim builder that assembles claims from coded encounters with automatic narrative generation
- REST API for claim lifecycle (create, list, get, status update)
- Coordination of benefits support (primary/secondary payer fields)
- Pre-authorization flag detection
