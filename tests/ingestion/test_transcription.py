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
    assert any(term in result.text.lower() for term in [
        "tooth", "composite", "crown", "prophy", "patient",
    ])
