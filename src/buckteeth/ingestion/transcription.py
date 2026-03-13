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
