import uuid
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
