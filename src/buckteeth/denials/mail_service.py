"""Mail service abstraction for sending physical complaint letters to insurance commissioners.

Provides an abstract base class plus a mock implementation (for testing/development)
and a Lob stub (for future production use with the Lob physical mail API).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MailResult:
    mail_id: str
    status: str  # created, in_transit, delivered, returned
    expected_delivery_date: str | None = None


class MailService(ABC):
    """Abstract base class for physical mail delivery services."""

    @abstractmethod
    async def send_letter(
        self,
        to_name: str,
        to_address_line1: str,
        to_city: str,
        to_state: str,
        to_zip: str,
        from_name: str,
        from_address_line1: str,
        from_city: str,
        from_state: str,
        from_zip: str,
        letter_html: str,
        **kwargs,
    ) -> MailResult: ...

    @abstractmethod
    async def check_status(self, mail_id: str) -> str: ...


class MockMailService(MailService):
    """In-memory mock mail service for testing and local development."""

    def __init__(self):
        self._letters: dict[str, dict] = {}

    async def send_letter(
        self,
        to_name: str,
        to_address_line1: str,
        to_city: str,
        to_state: str,
        to_zip: str,
        from_name: str,
        from_address_line1: str,
        from_city: str,
        from_state: str,
        from_zip: str,
        letter_html: str,
        **kwargs,
    ) -> MailResult:
        mail_id = f"MOCK-LTR-{uuid.uuid4().hex[:8].upper()}"
        self._letters[mail_id] = {"status": "created", "to_name": to_name}
        return MailResult(mail_id=mail_id, status="created", expected_delivery_date="2026-03-19")

    async def check_status(self, mail_id: str) -> str:
        letter = self._letters.get(mail_id)
        return letter["status"] if letter else "unknown"


class LobMailService(MailService):
    """Real Lob API integration for production physical mail delivery.

    Requires a valid LOB_API_KEY. See https://lob.com for API documentation.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def send_letter(
        self,
        to_name: str,
        to_address_line1: str,
        to_city: str,
        to_state: str,
        to_zip: str,
        from_name: str,
        from_address_line1: str,
        from_city: str,
        from_state: str,
        from_zip: str,
        letter_html: str,
        **kwargs,
    ) -> MailResult:
        raise NotImplementedError("Lob integration pending API key setup")

    async def check_status(self, mail_id: str) -> str:
        raise NotImplementedError("Lob integration pending API key setup")
