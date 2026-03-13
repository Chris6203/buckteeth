# Phase 5: Advanced Ingestion & Denial Risk Prediction

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AI ingestion pipeline with image analysis (x-rays/photos via Claude vision) and voice transcription (via mock transcription service), add pre-submission denial risk scoring that predicts denial probability before claims go out, and add ADA dental claim form PDF generation.

**Architecture:** Extend the existing `ingestion` module with image and voice parsers. New `risk` submodule under `denials` for pre-submission scoring. PDF generation as a new `forms` module. All Claude API calls mocked in tests. Voice transcription uses an abstract service interface (mock for dev, AWS Transcribe Medical for production).

**Tech Stack:** Same as prior phases, plus ReportLab for PDF generation, Pillow for image handling

---

## Chunk 1: Image Analysis & Voice Transcription

### Task 1: Image analyzer (Claude vision)

**Files:**
- Create: `src/buckteeth/ingestion/image_analyzer.py`
- Create: `tests/ingestion/test_image_analyzer.py`

- [ ] **Step 1: Write tests for image analyzer**

Create `tests/ingestion/test_image_analyzer.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.ingestion.image_analyzer import ImageAnalyzer
from buckteeth.ingestion.schemas import ParsedEncounter


@pytest.fixture
def analyzer():
    return ImageAnalyzer(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_analyze_xray(analyzer):
    mock_text = '{"procedures": [{"description": "Periapical radiolucency at apex of tooth #19 consistent with pulpal necrosis requiring root canal therapy", "tooth_numbers": [19], "surfaces": null, "quadrant": "lower left", "diagnosis": "pulpal necrosis"}], "notes": "Radiograph shows periapical pathology"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-image-bytes",
            media_type="image/png",
            context="Patient complains of pain on lower left",
        )
        assert isinstance(result, ParsedEncounter)
        assert len(result.procedures) == 1
        assert result.procedures[0].tooth_numbers == [19]


async def test_analyze_intraoral_photo(analyzer):
    mock_text = '{"procedures": [{"description": "Large carious lesion on occlusal surface of tooth #30", "tooth_numbers": [30], "surfaces": ["O"], "quadrant": "lower right", "diagnosis": "dental caries"}], "notes": "Visible cavitation"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-photo-bytes",
            media_type="image/jpeg",
            context="Routine exam",
        )
        assert len(result.procedures) == 1
        assert "O" in result.procedures[0].surfaces


async def test_analyze_with_no_findings(analyzer):
    mock_text = '{"procedures": [], "notes": "No abnormal findings on radiograph"}'
    with patch.object(analyzer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await analyzer.analyze(
            image_data=b"fake-image-bytes",
            media_type="image/png",
        )
        assert len(result.procedures) == 0
        assert "no abnormal" in result.notes.lower()
```

- [ ] **Step 2: Implement image analyzer**

Create `src/buckteeth/ingestion/image_analyzer.py`:

```python
import base64
import json
import re

import anthropic

from buckteeth.ingestion.schemas import ParsedEncounter

IMAGE_ANALYSIS_SYSTEM_PROMPT = """\
You are a dental radiograph and clinical image analyst. Your job is to extract \
clinical findings from dental images (radiographs, intraoral photos, panoramic X-rays).

You should identify:
- Carious lesions (cavities) with location and severity
- Periapical pathology (abscess, radiolucency)
- Bone loss patterns (horizontal, vertical, generalized, localized)
- Fractures or cracks
- Failing restorations
- Impacted teeth
- Any other clinically significant findings

Return your response as JSON:
{
  "procedures": [
    {
      "description": "Detailed clinical finding and recommended procedure",
      "tooth_numbers": [14],
      "surfaces": ["M", "O", "D"],
      "quadrant": "upper right",
      "diagnosis": "diagnosis or finding"
    }
  ],
  "notes": "Additional observations"
}

Rules:
- "procedures" is always an array (empty if no findings).
- Only report findings you can clearly identify in the image.
- Surface abbreviations: M, O, D, L, B, F, I.
- Return ONLY valid JSON. No additional text.
"""


class ImageAnalyzer:
    """Analyzes dental images using Claude's vision capabilities."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze(
        self,
        image_data: bytes,
        media_type: str = "image/png",
        context: str | None = None,
    ) -> ParsedEncounter:
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
        ]
        if context:
            user_content.append({"type": "text", "text": f"Clinical context: {context}"})
        else:
            user_content.append({"type": "text", "text": "Analyze this dental image."})

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=IMAGE_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw_text = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        data = json.loads(cleaned)
        return ParsedEncounter.model_validate(data)
```

- [ ] **Step 3: Run tests, commit**

### Task 2: Voice transcription pipeline

**Files:**
- Create: `src/buckteeth/ingestion/transcription.py`
- Create: `tests/ingestion/test_transcription.py`

- [ ] **Step 1: Write tests for transcription service**

Create `tests/ingestion/test_transcription.py`:

```python
import pytest
from buckteeth.ingestion.transcription import MockTranscriptionService, TranscriptionResult


@pytest.fixture
def service():
    return MockTranscriptionService()


async def test_transcribe_audio(service):
    result = await service.transcribe(
        audio_data=b"fake-audio-bytes",
        audio_format="wav",
    )
    assert isinstance(result, TranscriptionResult)
    assert len(result.text) > 0
    assert result.confidence > 0


async def test_transcribe_returns_dental_text(service):
    result = await service.transcribe(
        audio_data=b"fake-audio-bytes",
        audio_format="wav",
    )
    # Mock should return realistic dental dictation
    assert any(term in result.text.lower() for term in [
        "tooth", "composite", "crown", "prophy", "patient",
    ])
```

- [ ] **Step 2: Implement transcription service**

Create `src/buckteeth/ingestion/transcription.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    confidence: float  # 0.0-1.0
    language: str = "en-US"


class TranscriptionService(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> TranscriptionResult: ...


class MockTranscriptionService(TranscriptionService):
    """Mock for development and testing. Returns realistic dental dictation."""

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> TranscriptionResult:
        return TranscriptionResult(
            text=(
                "Patient presents for scheduled crown preparation on tooth number 30. "
                "Existing large MOD amalgam with recurrent decay noted on distal margin. "
                "Administered local anesthetic, 2 carpules of lidocaine with epinephrine. "
                "Removed old restoration and decay. Buildup placed with composite core material. "
                "Crown preparation completed with chamfer margin. Impression taken with PVS material. "
                "Temporary crown fabricated and cemented with TempBond."
            ),
            confidence=0.95,
        )


class AWSTranscribeService(TranscriptionService):
    """AWS Transcribe Medical integration. Requires AWS credentials."""

    def __init__(self, region: str = "us-east-1"):
        self._region = region

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> TranscriptionResult:
        raise NotImplementedError("AWS Transcribe integration pending credentials setup")
```

- [ ] **Step 3: Run tests, commit**

### Task 3: Image and voice API endpoints

**Files:**
- Modify: `src/buckteeth/api/schemas.py` (add image/voice schemas)
- Modify: `src/buckteeth/api/encounters.py` (add image and voice endpoints)
- Create: `tests/api/test_encounters_advanced.py`

- [ ] **Step 1: Add schemas to `src/buckteeth/api/schemas.py`**

Append after the existing Encounter section:

```python
class EncounterFromImageRequest(BaseModel):
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
    context: str | None = None

class EncounterFromVoiceRequest(BaseModel):
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
```

- [ ] **Step 2: Add endpoints to `src/buckteeth/api/encounters.py`**

Add two new endpoints:

`POST /from-image` (201) — Accepts multipart form with image file + metadata. Runs image through ImageAnalyzer, creates ClinicalEncounter with raw_input_type="image".

`POST /from-voice` (201) — Accepts multipart form with audio file + metadata. Transcribes via TranscriptionService, then parses transcribed text via ClinicalNoteParser. Creates ClinicalEncounter with raw_input_type="voice".

```python
from fastapi import File, Form, UploadFile
from buckteeth.ingestion.image_analyzer import ImageAnalyzer
from buckteeth.ingestion.transcription import MockTranscriptionService


@router.post("/from-image", response_model=EncounterResponse, status_code=201)
async def create_encounter_from_image(
    patient_id: uuid.UUID = Form(...),
    provider_name: str = Form(...),
    date_of_service: str = Form(...),
    context: str = Form(default=""),
    image: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    image_data = await image.read()
    media_type = image.content_type or "image/png"

    analyzer = ImageAnalyzer(api_key=settings.anthropic_api_key)
    parsed = await analyzer.analyze(image_data, media_type, context or None)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient_id,
        provider_name=provider_name,
        date_of_service=date_of_service,
        raw_notes=f"[Image analysis] {context}" if context else "[Image analysis]",
        raw_input_type="image",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in parsed.procedures:
        clinical_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers=proc.tooth_numbers,
            surfaces=proc.surfaces,
            quadrant=proc.quadrant,
            diagnosis=proc.diagnosis,
        )
        session.add(clinical_proc)

    await session.flush()
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()


@router.post("/from-voice", response_model=EncounterResponse, status_code=201)
async def create_encounter_from_voice(
    patient_id: uuid.UUID = Form(...),
    provider_name: str = Form(...),
    date_of_service: str = Form(...),
    audio: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    audio_data = await audio.read()
    audio_format = "wav"
    if audio.content_type:
        if "mp3" in audio.content_type:
            audio_format = "mp3"
        elif "ogg" in audio.content_type:
            audio_format = "ogg"

    transcription_service = MockTranscriptionService()
    transcription = await transcription_service.transcribe(audio_data, audio_format)

    parser = ClinicalNoteParser(api_key=settings.anthropic_api_key)
    parsed = await parser.parse(transcription.text)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient_id,
        provider_name=provider_name,
        date_of_service=date_of_service,
        raw_notes=transcription.text,
        raw_input_type="voice",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in parsed.procedures:
        clinical_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers=proc.tooth_numbers,
            surfaces=proc.surfaces,
            quadrant=proc.quadrant,
            diagnosis=proc.diagnosis,
        )
        session.add(clinical_proc)

    await session.flush()
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()
```

- [ ] **Step 3: Write tests**

Create `tests/api/test_encounters_advanced.py`:

```python
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.database import get_db
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure
from buckteeth.ingestion.transcription import TranscriptionResult
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


async def _create_patient(client):
    resp = await client.post(
        "/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "1990-01-15",
            "gender": "F",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    return resp.json()["id"]


async def test_create_encounter_from_image(client, engine):
    patient_id = await _create_patient(client)

    mock_parsed = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="Periapical radiolucency tooth #19",
                tooth_numbers=[19],
                surfaces=None,
                quadrant="lower left",
                diagnosis="pulpal necrosis",
            ),
        ],
        notes="Radiograph findings",
    )

    with patch("buckteeth.api.encounters.ImageAnalyzer") as MockAnalyzer:
        MockAnalyzer.return_value.analyze = AsyncMock(return_value=mock_parsed)

        response = await client.post(
            "/v1/encounters/from-image",
            data={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "context": "Pain on lower left",
            },
            files={"image": ("xray.png", b"fake-image-bytes", "image/png")},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["raw_input_type"] == "image"
    assert len(data["procedures"]) == 1
    assert data["procedures"][0]["diagnosis"] == "pulpal necrosis"


async def test_create_encounter_from_voice(client, engine):
    patient_id = await _create_patient(client)

    mock_transcription = TranscriptionResult(
        text="Crown prep on tooth 30 with MOD decay",
        confidence=0.95,
    )
    mock_parsed = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="Crown preparation",
                tooth_numbers=[30],
                surfaces=["M", "O", "D"],
                quadrant="lower right",
                diagnosis="recurrent decay",
            ),
        ],
        notes="Dictated note",
    )

    with patch("buckteeth.api.encounters.MockTranscriptionService") as MockTranscribe, \
         patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        MockTranscribe.return_value.transcribe = AsyncMock(return_value=mock_transcription)
        MockParser.return_value.parse = AsyncMock(return_value=mock_parsed)

        response = await client.post(
            "/v1/encounters/from-voice",
            data={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
            },
            files={"audio": ("dictation.wav", b"fake-audio-bytes", "audio/wav")},
            headers={"X-Tenant-ID": TENANT_ID},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["raw_input_type"] == "voice"
    assert len(data["procedures"]) == 1
    assert data["procedures"][0]["description"] == "Crown preparation"
```

- [ ] **Step 4: Run all tests, commit**

---

## Chunk 2: Pre-Submission Denial Risk Scoring

### Task 4: Denial risk prediction model

**Files:**
- Create: `src/buckteeth/denials/risk_scorer.py`
- Create: `tests/denials/test_risk_scorer.py`

- [ ] **Step 1: Write tests**

Create `tests/denials/test_risk_scorer.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.denials.risk_scorer import DenialRiskScorer, RiskAssessment


@pytest.fixture
def scorer():
    return DenialRiskScorer(api_key="test-key")


def _mock_claude_response(text: str) -> MagicMock:
    mock_block = MagicMock()
    mock_block.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_assess_low_risk(scorer):
    mock_text = '{"risk_score": 15, "risk_level": "low", "risk_factors": [], "recommendations": ["Claim looks routine, proceed with submission"]}'
    with patch.object(scorer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await scorer.assess(
            cdt_codes=["D1110"],
            payer_name="Delta Dental",
            payer_id="DD001",
            patient_age=35,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Routine prophylaxis, healthy patient",
        )
        assert isinstance(result, RiskAssessment)
        assert result.risk_score <= 30
        assert result.risk_level == "low"


async def test_assess_high_risk(scorer):
    mock_text = '{"risk_score": 78, "risk_level": "high", "risk_factors": ["Crown frequency limit: last crown on this tooth within 5 years", "Missing pre-authorization for major procedure", "Payer frequently denies D2740 without radiographic evidence"], "recommendations": ["Obtain pre-authorization before submission", "Attach periapical radiograph showing clinical necessity", "Include detailed clinical narrative"]}'
    with patch.object(scorer._client.messages, "create",
                      new_callable=AsyncMock,
                      return_value=_mock_claude_response(mock_text)):
        result = await scorer.assess(
            cdt_codes=["D2740"],
            payer_name="MetLife",
            payer_id="ML001",
            patient_age=45,
            provider_name="Dr. Smith",
            date_of_service="2026-03-12",
            clinical_notes="Crown on #30, previous crown 3 years ago",
        )
        assert result.risk_score >= 60
        assert result.risk_level == "high"
        assert len(result.risk_factors) > 0
        assert len(result.recommendations) > 0


def test_rule_based_frequency_check(scorer):
    factors = scorer._check_frequency_risks(
        cdt_codes=["D0274"],  # BWX - typically 1x/year
        payer_name="Delta Dental",
        last_service_dates={"D0274": "2026-01-15"},
    )
    assert len(factors) > 0  # Should flag recent BWX


def test_rule_based_no_frequency_issue(scorer):
    factors = scorer._check_frequency_risks(
        cdt_codes=["D1110"],  # Prophy - 2x/year
        payer_name="Delta Dental",
        last_service_dates={"D1110": "2025-09-01"},
    )
    assert len(factors) == 0  # 6+ months ago, should be fine
```

- [ ] **Step 2: Implement risk scorer**

Create `src/buckteeth/denials/risk_scorer.py`:

```python
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

import anthropic

from buckteeth.knowledge.payer_rules import PayerRuleRepository


@dataclass
class RiskAssessment:
    risk_score: int  # 0-100
    risk_level: str  # low, medium, high
    risk_factors: list[str]
    recommendations: list[str]


RISK_SYSTEM_PROMPT = """\
You are a dental insurance claims risk analyst. Your job is to predict the \
likelihood of claim denial BEFORE submission.

Analyze the claim details and assess denial risk based on:
1. Procedure type and payer patterns (certain payers frequently deny specific codes)
2. Frequency limitations (e.g., crowns every 5 years, BWX 1x/year, prophy 2x/year)
3. Missing documentation (narratives, x-rays, pre-authorization)
4. Code bundling issues
5. Patient age appropriateness for procedures
6. Known payer-specific denial patterns

Return as JSON:
{
  "risk_score": <0-100>,
  "risk_level": "<low|medium|high>",
  "risk_factors": ["<list of specific risk factors>"],
  "recommendations": ["<list of actions to reduce denial risk>"]
}

Risk levels: low (0-30), medium (31-60), high (61-100)
Return ONLY the JSON object.
"""


# Common frequency limits in months
FREQUENCY_LIMITS = {
    "D0120": 6,     # Periodic oral eval - 2x/year
    "D0150": 36,    # Comprehensive oral eval - every 3 years
    "D0210": 60,    # FMX - every 5 years
    "D0274": 12,    # BWX - 1x/year
    "D1110": 6,     # Prophy - 2x/year
    "D1120": 6,     # Child prophy - 2x/year
    "D2740": 60,    # Crown porcelain - every 5 years
    "D2750": 60,    # Crown porcelain-metal - every 5 years
    "D4341": 24,    # SRP - every 2 years
    "D4342": 24,    # SRP 1-3 teeth - every 2 years
}


class DenialRiskScorer:
    """Predicts denial probability using rule-based checks + Claude analysis."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._payer_rules = PayerRuleRepository()

    async def assess(
        self,
        cdt_codes: list[str],
        payer_name: str,
        payer_id: str,
        patient_age: int,
        provider_name: str,
        date_of_service: str,
        clinical_notes: str,
        last_service_dates: dict[str, str] | None = None,
    ) -> RiskAssessment:
        # 1. Rule-based pre-checks
        rule_factors = self._check_frequency_risks(
            cdt_codes, payer_name, last_service_dates or {}
        )

        # 2. Claude-based risk analysis
        user_prompt = self._build_prompt(
            cdt_codes, payer_name, patient_age, provider_name,
            date_of_service, clinical_notes, rule_factors,
        )

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=RISK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text
        data = json.loads(raw_text)

        return RiskAssessment(
            risk_score=data["risk_score"],
            risk_level=data["risk_level"],
            risk_factors=data["risk_factors"],
            recommendations=data["recommendations"],
        )

    def _check_frequency_risks(
        self,
        cdt_codes: list[str],
        payer_name: str,
        last_service_dates: dict[str, str],
    ) -> list[str]:
        factors = []
        today = datetime.now().date()

        for code in cdt_codes:
            limit_months = FREQUENCY_LIMITS.get(code)
            if limit_months is None:
                continue

            last_date_str = last_service_dates.get(code)
            if last_date_str is None:
                continue

            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            months_since = (today - last_date).days / 30.44

            if months_since < limit_months:
                factors.append(
                    f"Frequency limit: {code} last performed {last_date_str} "
                    f"({months_since:.0f} months ago), "
                    f"typical limit is {limit_months} months"
                )

        return factors

    @staticmethod
    def _build_prompt(cdt_codes, payer_name, patient_age, provider_name,
                      date_of_service, clinical_notes, rule_factors) -> str:
        rule_section = ""
        if rule_factors:
            rule_section = "\n\nPre-identified risk factors:\n" + "\n".join(
                f"- {f}" for f in rule_factors
            )

        return f"""Claim Details:
- CDT Codes: {', '.join(cdt_codes)}
- Payer: {payer_name}
- Patient Age: {patient_age}
- Provider: {provider_name}
- Date of Service: {date_of_service}

Clinical Notes:
{clinical_notes}
{rule_section}

Assess the denial risk for this claim."""
```

- [ ] **Step 3: Run tests, commit**

### Task 5: Risk scoring API endpoint

**Files:**
- Modify: `src/buckteeth/api/schemas.py` (add risk schemas)
- Modify: `src/buckteeth/api/claims.py` (add risk assessment endpoint)
- Create: `tests/api/test_claims_risk.py`

- [ ] **Step 1: Add risk schemas to `src/buckteeth/api/schemas.py`**

Append after the ClaimStatusUpdate class:

```python
class RiskAssessmentRequest(BaseModel):
    last_service_dates: dict[str, str] | None = None
    patient_age: int = 35

class RiskAssessmentResponse(BaseModel):
    risk_score: int
    risk_level: str
    risk_factors: list[str]
    recommendations: list[str]
```

- [ ] **Step 2: Add endpoint to `src/buckteeth/api/claims.py`**

Add endpoint: `POST /v1/claims/{claim_id}/assess-risk` (200)

Loads claim + patient from DB, extracts CDT codes from claim procedures, calls DenialRiskScorer, returns RiskAssessmentResponse.

```python
from buckteeth.denials.risk_scorer import DenialRiskScorer

@router.post("/{claim_id}/assess-risk", response_model=RiskAssessmentResponse)
async def assess_denial_risk(
    claim_id: uuid.UUID,
    body: RiskAssessmentRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(Claim.id == claim_id, Claim.tenant_id == tenant_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    cdt_codes = [p.cdt_code for p in claim.procedures]

    scorer = DenialRiskScorer(api_key=settings.anthropic_api_key)
    assessment = await scorer.assess(
        cdt_codes=cdt_codes,
        payer_name=claim.primary_payer_name,
        payer_id=claim.primary_payer_id,
        patient_age=body.patient_age,
        provider_name=claim.provider_name,
        date_of_service=claim.date_of_service,
        clinical_notes=f"Claim for {', '.join(cdt_codes)}",
        last_service_dates=body.last_service_dates,
    )

    return RiskAssessmentResponse(
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        risk_factors=assessment.risk_factors,
        recommendations=assessment.recommendations,
    )
```

- [ ] **Step 3: Write tests**

Create `tests/api/test_claims_risk.py`:

```python
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

    # Create patient
    patient_resp = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe",
              "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = patient_resp.json()["id"]

    # Add insurance
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

    # Create encounter
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

    # Code encounter
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        MockEngine.return_value.code_encounter = AsyncMock(
            return_value=_mock_coding_result())
        code_resp = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "default"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    coded_enc_id = code_resp.json()["id"]

    # Build claim
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
```

- [ ] **Step 4: Run all tests, commit**

---

## Chunk 3: ADA Dental Claim Form PDF

### Task 6: ADA claim form PDF generation

**Files:**
- Create: `src/buckteeth/forms/__init__.py`
- Create: `src/buckteeth/forms/ada_claim.py`
- Create: `tests/forms/__init__.py`
- Create: `tests/forms/test_ada_claim.py`

- [ ] **Step 1: Write tests**

Create `tests/forms/test_ada_claim.py`:

```python
import uuid
import pytest
from buckteeth.forms.ada_claim import ADAClaimFormGenerator, ClaimFormData, ProcedureLineItem


@pytest.fixture
def generator():
    return ADAClaimFormGenerator()


@pytest.fixture
def sample_claim_data():
    return ClaimFormData(
        patient_name="Jane Doe",
        patient_dob="01/15/1990",
        patient_address="123 Main St, Los Angeles, CA 90001",
        patient_gender="F",
        subscriber_name="Jane Doe",
        subscriber_id="SUB123",
        group_number="GRP456",
        payer_name="Delta Dental",
        payer_address="PO Box 997330, Sacramento, CA 95899",
        provider_name="Dr. John Smith, DDS",
        provider_npi="1234567890",
        provider_license="CA-12345",
        provider_address="456 Dental Ave, Los Angeles, CA 90002",
        provider_tax_id="12-3456789",
        date_of_service="03/12/2026",
        procedures=[
            ProcedureLineItem(
                line_number=1,
                cdt_code="D2740",
                tooth_number="30",
                surfaces="",
                description="Crown - porcelain/ceramic",
                fee=1200.00,
            ),
        ],
        total_fee=1200.00,
    )


def test_generate_pdf(generator, sample_claim_data):
    pdf_bytes = generator.generate(sample_claim_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"  # Valid PDF header


def test_generate_pdf_multiple_procedures(generator, sample_claim_data):
    sample_claim_data.procedures.append(
        ProcedureLineItem(
            line_number=2,
            cdt_code="D2950",
            tooth_number="30",
            surfaces="",
            description="Core buildup",
            fee=350.00,
        )
    )
    sample_claim_data.total_fee = 1550.00
    pdf_bytes = generator.generate(sample_claim_data)
    assert pdf_bytes[:4] == b"%PDF"
```

- [ ] **Step 2: Implement ADA claim form generator**

Create `src/buckteeth/forms/ada_claim.py`:

```python
from dataclasses import dataclass, field
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@dataclass
class ProcedureLineItem:
    line_number: int
    cdt_code: str
    tooth_number: str
    surfaces: str
    description: str
    fee: float


@dataclass
class ClaimFormData:
    # Patient info
    patient_name: str
    patient_dob: str
    patient_address: str
    patient_gender: str
    # Subscriber info
    subscriber_name: str
    subscriber_id: str
    group_number: str
    # Payer info
    payer_name: str
    payer_address: str
    # Provider info
    provider_name: str
    provider_npi: str
    provider_license: str
    provider_address: str
    provider_tax_id: str
    # Claim info
    date_of_service: str
    procedures: list[ProcedureLineItem] = field(default_factory=list)
    total_fee: float = 0.0
    preauth_number: str | None = None


class ADAClaimFormGenerator:
    """Generates ADA Dental Claim Form PDFs."""

    def generate(self, data: ClaimFormData) -> bytes:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 0.75 * inch, "ADA Dental Claim Form")

        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, height - 1.0 * inch,
                            "Standard form for dental insurance claim submission")

        y = height - 1.5 * inch

        # Payer Information
        y = self._draw_section(c, "INSURANCE COMPANY / DENTAL BENEFIT PLAN", y, [
            ("Payer Name", data.payer_name),
            ("Payer Address", data.payer_address),
        ])

        # Patient Information
        y = self._draw_section(c, "PATIENT INFORMATION", y - 0.2 * inch, [
            ("Patient Name", data.patient_name),
            ("Date of Birth", data.patient_dob),
            ("Gender", data.patient_gender),
            ("Address", data.patient_address),
        ])

        # Subscriber Information
        y = self._draw_section(c, "SUBSCRIBER INFORMATION", y - 0.2 * inch, [
            ("Subscriber Name", data.subscriber_name),
            ("Subscriber ID", data.subscriber_id),
            ("Group Number", data.group_number),
        ])

        # Provider Information
        y = self._draw_section(c, "BILLING DENTIST", y - 0.2 * inch, [
            ("Provider Name", data.provider_name),
            ("NPI", data.provider_npi),
            ("License #", data.provider_license),
            ("Tax ID", data.provider_tax_id),
            ("Address", data.provider_address),
        ])

        if data.preauth_number:
            y = self._draw_section(c, "PRE-AUTHORIZATION", y - 0.2 * inch, [
                ("Pre-Authorization #", data.preauth_number),
            ])

        # Procedures table
        y -= 0.3 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y, "PROCEDURES")
        y -= 0.2 * inch

        # Table header
        c.setFont("Helvetica-Bold", 8)
        cols = [0.5, 1.0, 2.0, 2.8, 3.5, 6.5]
        headers = ["#", "Date", "CDT Code", "Tooth", "Surface", "Description", "Fee"]
        for i, (col_x, header) in enumerate(zip(cols, headers)):
            c.drawString(col_x * inch, y, header)
        c.drawString(6.5 * inch, y, "Fee")
        y -= 0.05 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.15 * inch

        # Procedure lines
        c.setFont("Helvetica", 8)
        for proc in data.procedures:
            c.drawString(0.5 * inch, y, str(proc.line_number))
            c.drawString(1.0 * inch, y, data.date_of_service)
            c.drawString(2.0 * inch, y, proc.cdt_code)
            c.drawString(2.8 * inch, y, proc.tooth_number)
            c.drawString(3.5 * inch, y, proc.surfaces)
            c.drawString(4.2 * inch, y, proc.description[:30])
            c.drawRightString(7.5 * inch, y, f"${proc.fee:,.2f}")
            y -= 0.2 * inch

        # Total
        y -= 0.1 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.2 * inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(4.2 * inch, y, "TOTAL FEE:")
        c.drawRightString(7.5 * inch, y, f"${data.total_fee:,.2f}")

        c.save()
        return buffer.getvalue()

    @staticmethod
    def _draw_section(c, title, y, fields):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y, title)
        y -= 0.05 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.18 * inch

        c.setFont("Helvetica", 9)
        for label, value in fields:
            c.drawString(0.5 * inch, y, f"{label}:")
            c.drawString(2.2 * inch, y, str(value))
            y -= 0.18 * inch

        return y
```

- [ ] **Step 3: Add PDF download API endpoint**

Modify `src/buckteeth/api/claims.py` to add:

`GET /v1/claims/{claim_id}/pdf` — Generates and returns the ADA dental claim form PDF for a claim.

```python
from fastapi.responses import Response
from buckteeth.forms.ada_claim import ADAClaimFormGenerator, ClaimFormData, ProcedureLineItem

@router.get("/{claim_id}/pdf")
async def download_claim_pdf(
    claim_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(Claim.id == claim_id, Claim.tenant_id == tenant_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Load patient
    from buckteeth.models.patient import Patient, InsurancePlan
    patient_result = await session.execute(
        select(Patient).where(Patient.id == claim.patient_id)
    )
    patient = patient_result.scalar_one_or_none()

    procedure_lines = []
    for i, proc in enumerate(claim.procedures, 1):
        procedure_lines.append(ProcedureLineItem(
            line_number=i,
            cdt_code=proc.cdt_code,
            tooth_number=proc.tooth_number or "",
            surfaces=proc.surfaces or "",
            description=proc.cdt_description,
            fee=proc.fee_submitted or 0.0,
        ))

    form_data = ClaimFormData(
        patient_name=f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
        patient_dob=patient.date_of_birth if patient else "",
        patient_address="",
        patient_gender=patient.gender if patient else "",
        subscriber_name=f"{patient.first_name} {patient.last_name}" if patient else "",
        subscriber_id=claim.primary_subscriber_id,
        group_number=claim.primary_group_number,
        payer_name=claim.primary_payer_name,
        payer_address="",
        provider_name=claim.provider_name,
        provider_npi="",
        provider_license="",
        provider_address="",
        provider_tax_id="",
        date_of_service=claim.date_of_service,
        procedures=procedure_lines,
        total_fee=claim.total_fee_submitted or 0.0,
        preauth_number=claim.preauth_number,
    )

    generator = ADAClaimFormGenerator()
    pdf_bytes = generator.generate(form_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=claim-{claim_id}.pdf"},
    )
```

- [ ] **Step 4: Write PDF endpoint test**

Add to `tests/api/test_claims_risk.py`:

```python
async def test_download_claim_pdf(client, engine):
    claim_id = await _create_claim(client, engine)

    response = await client.get(
        f"/v1/claims/{claim_id}/pdf",
        headers={"X-Tenant-ID": TENANT_ID},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"
```

- [ ] **Step 5: Run all tests, commit**

---

## Phase 5 Summary

Phase 5 delivers:
- Image analysis via Claude vision (x-rays, intraoral photos)
- Voice transcription pipeline (mock + AWS Transcribe stub)
- API endpoints for image and voice encounter creation
- Pre-submission denial risk scoring (rule-based + Claude)
- Risk assessment API endpoint on claims
- ADA dental claim form PDF generation
- PDF download API endpoint
