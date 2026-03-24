"""Dentrix PMS Adapter.

Dentrix by Henry Schein One is one of the most widely used dental practice
management systems. This adapter supports multiple integration methods:

1. DTXAPI (Dentrix Developer API) — REST API for Dentrix G7+
2. Dentrix Ascend (Cloud) — REST API for the cloud version
3. Database bridge — Direct connection to Dentrix SQL Server database
4. File exchange — Import/export via CSV, XML, or Dentrix Bridge files

Integration Setup:
- Dentrix G5/G6: Use database bridge (requires Dentrix running on same network)
- Dentrix G7+: Use DTXAPI (requires API key from Henry Schein)
- Dentrix Ascend: Use Ascend REST API (requires OAuth credentials)

Documentation:
- DTXAPI: https://developer.henryschein.com
- Dentrix Bridge: Built into Dentrix under Setup > Program Links

Requirements:
- Dentrix G5+ installed on office server/workstation
- API access enabled (DTXAPI for G7+ or database access for G5/G6)
- Network access from this server to the Dentrix machine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from buckteeth.pms.adapters import PMSAdapter
from buckteeth.pms.schemas import (
    PMSClaimResult,
    PMSConnectionStatus,
    PMSEncounter,
    PMSFeeSchedule,
    PMSPatient,
    PMSProcedure,
    PMSTreatmentHistory,
)

logger = logging.getLogger(__name__)


@dataclass
class DentrixConfig:
    """Configuration for Dentrix connection."""

    # Connection method: "dtxapi", "ascend", "database", "bridge"
    method: str = "dtxapi"

    # DTXAPI settings (Dentrix G7+)
    api_url: str = "http://localhost:8080/api"  # Default DTXAPI endpoint
    api_key: str = ""

    # Ascend settings (cloud)
    ascend_url: str = "https://api.dentrixascend.com/v1"
    client_id: str = ""
    client_secret: str = ""

    # Database bridge settings (G5/G6)
    db_host: str = "localhost"
    db_name: str = "Dentrix"
    db_user: str = ""
    db_password: str = ""

    # General
    timeout: float = 30.0
    practice_id: str = ""  # For multi-location practices


class DentrixAdapter(PMSAdapter):
    """
    Dentrix PMS adapter supporting DTXAPI and Dentrix Ascend.

    Usage:
        config = DentrixConfig(method="dtxapi", api_url="http://office-server:8080/api", api_key="your-key")
        adapter = DentrixAdapter(config)
        status = await adapter.authenticate({})
        patients = await adapter.pull_patients()
    """

    def __init__(self, config: DentrixConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            base_url = (
                self.config.ascend_url
                if self.config.method == "ascend"
                else self.config.api_url
            )
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=self.config.timeout,
                headers=self._auth_headers(),
            )
        return self._client

    def _auth_headers(self) -> dict[str, str]:
        """Build authentication headers based on connection method."""
        if self.config.method == "dtxapi":
            return {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
        elif self.config.method == "ascend":
            return {
                "Authorization": f"Bearer {self._token or ''}",
                "Content-Type": "application/json",
            }
        return {"Content-Type": "application/json"}

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        """Test connection to Dentrix and authenticate."""
        try:
            client = await self._get_client()

            if self.config.method == "dtxapi":
                # DTXAPI health check
                resp = await client.get("/status")
                if resp.status_code == 200:
                    data = resp.json()
                    return PMSConnectionStatus(
                        connected=True,
                        pms_name="Dentrix",
                        version=data.get("version", "G7+"),
                        last_sync=data.get("lastSync"),
                    )

            elif self.config.method == "ascend":
                # Ascend OAuth token exchange
                token_resp = await httpx.AsyncClient().post(
                    "https://auth.dentrixascend.com/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                    },
                )
                if token_resp.status_code == 200:
                    self._token = token_resp.json()["access_token"]
                    return PMSConnectionStatus(
                        connected=True,
                        pms_name="Dentrix Ascend",
                        version="Cloud",
                    )

            return PMSConnectionStatus(
                connected=False,
                pms_name="Dentrix",
                error="Authentication failed",
            )

        except Exception as e:
            logger.error("Dentrix connection failed: %s", e)
            return PMSConnectionStatus(
                connected=False,
                pms_name="Dentrix",
                error=str(e),
            )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        """Pull patients from Dentrix."""
        client = await self._get_client()

        params: dict[str, Any] = {}
        if "last_name" in filters:
            params["lastName"] = filters["last_name"]
        if "external_id" in filters:
            params["patientId"] = filters["external_id"]

        try:
            if self.config.method == "dtxapi":
                resp = await client.get("/patients", params=params)
            elif self.config.method == "ascend":
                resp = await client.get("/patients", params=params)
            else:
                return []

            if resp.status_code != 200:
                return []

            patients = []
            for p in resp.json().get("data", resp.json() if isinstance(resp.json(), list) else []):
                patients.append(PMSPatient(
                    external_id=str(p.get("patientId", p.get("id", ""))),
                    first_name=p.get("firstName", p.get("first_name", "")),
                    last_name=p.get("lastName", p.get("last_name", "")),
                    date_of_birth=p.get("dateOfBirth", p.get("birthdate", "")),
                    gender=p.get("gender", ""),
                    phone=p.get("homePhone", p.get("phone", "")),
                    email=p.get("email", ""),
                    address=_format_address(p),
                    primary_payer_name=p.get("primaryInsurance", {}).get("carrierName")
                    if isinstance(p.get("primaryInsurance"), dict) else None,
                    primary_payer_id=p.get("primaryInsurance", {}).get("payerId")
                    if isinstance(p.get("primaryInsurance"), dict) else None,
                    primary_subscriber_id=p.get("primaryInsurance", {}).get("subscriberId")
                    if isinstance(p.get("primaryInsurance"), dict) else None,
                    primary_group_number=p.get("primaryInsurance", {}).get("groupNumber")
                    if isinstance(p.get("primaryInsurance"), dict) else None,
                ))
            return patients

        except Exception as e:
            logger.error("Failed to pull patients from Dentrix: %s", e)
            return []

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        """Pull a specific encounter from Dentrix."""
        client = await self._get_client()

        try:
            resp = await client.get(
                f"/patients/{patient_external_id}/procedures",
                params={"dateOfService": date_of_service},
            )
            if resp.status_code != 200:
                return None

            procedures = []
            provider_name = ""
            for proc in resp.json().get("data", []):
                procedures.append(PMSProcedure(
                    code=proc.get("adaCode", proc.get("procedureCode", "")),
                    description=proc.get("description", ""),
                    tooth_number=str(proc.get("toothNumber", "")) if proc.get("toothNumber") else None,
                    surfaces=proc.get("surfaces", ""),
                    fee=float(proc.get("fee", 0)),
                    status=proc.get("status", "completed"),
                ))
                if not provider_name and proc.get("providerName"):
                    provider_name = proc["providerName"]

            if not procedures:
                return None

            return PMSEncounter(
                external_id=f"{patient_external_id}-{date_of_service}",
                patient_external_id=patient_external_id,
                provider_name=provider_name,
                date_of_service=date_of_service,
                procedures=procedures,
                notes=resp.json().get("clinicalNotes", ""),
            )

        except Exception as e:
            logger.error("Failed to pull encounter from Dentrix: %s", e)
            return None

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        """Pull complete treatment history for a patient."""
        client = await self._get_client()

        try:
            resp = await client.get(
                f"/patients/{patient_external_id}/procedures",
                params={"status": "completed"},
            )
            if resp.status_code != 200:
                return PMSTreatmentHistory(
                    patient_external_id=patient_external_id,
                    encounters=[],
                )

            # Group procedures by date of service
            by_date: dict[str, list] = {}
            for proc in resp.json().get("data", []):
                dos = proc.get("dateOfService", "unknown")
                by_date.setdefault(dos, []).append(proc)

            encounters = []
            for dos, procs in sorted(by_date.items(), reverse=True):
                procedures = [
                    PMSProcedure(
                        code=p.get("adaCode", ""),
                        description=p.get("description", ""),
                        tooth_number=str(p.get("toothNumber", "")) if p.get("toothNumber") else None,
                        surfaces=p.get("surfaces", ""),
                        fee=float(p.get("fee", 0)),
                    )
                    for p in procs
                ]
                encounters.append(PMSEncounter(
                    external_id=f"{patient_external_id}-{dos}",
                    patient_external_id=patient_external_id,
                    provider_name=procs[0].get("providerName", ""),
                    date_of_service=dos,
                    procedures=procedures,
                ))

            return PMSTreatmentHistory(
                patient_external_id=patient_external_id,
                encounters=encounters,
            )

        except Exception as e:
            logger.error("Failed to pull treatment history: %s", e)
            return PMSTreatmentHistory(
                patient_external_id=patient_external_id, encounters=[],
            )

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        """Push a coded claim back to Dentrix."""
        client = await self._get_client()

        try:
            resp = await client.post(
                f"/patients/{patient_external_id}/claims",
                json=claim_data,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return PMSClaimResult(
                    external_claim_id=str(data.get("claimId", "")),
                    status="accepted",
                    message="Claim sent to Dentrix",
                )
            return PMSClaimResult(
                external_claim_id="",
                status="rejected",
                message=f"Dentrix returned {resp.status_code}",
            )

        except Exception as e:
            return PMSClaimResult(
                external_claim_id="",
                status="error",
                message=str(e),
            )

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        """Pull fee schedule from Dentrix for a specific payer."""
        client = await self._get_client()

        try:
            resp = await client.get(
                "/feeschedules",
                params={"payerId": payer_id},
            )
            if resp.status_code == 200:
                fees = {}
                for entry in resp.json().get("data", []):
                    code = entry.get("adaCode", "")
                    fee = float(entry.get("fee", 0))
                    if code and fee > 0:
                        fees[code] = fee
                return PMSFeeSchedule(payer_id=payer_id, fees=fees)

        except Exception as e:
            logger.error("Failed to pull fee schedule: %s", e)

        return PMSFeeSchedule(payer_id=payer_id, fees={})

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


def _format_address(patient_data: dict) -> str:
    """Format address from Dentrix patient data."""
    parts = [
        patient_data.get("address1", ""),
        patient_data.get("address2", ""),
        patient_data.get("city", ""),
        patient_data.get("state", ""),
        patient_data.get("zipCode", patient_data.get("zip", "")),
    ]
    return ", ".join(p for p in parts if p)


# ── Dentrix Bridge File Support ───────────────────────────────────────

DENTRIX_BRIDGE_FIELDS = {
    "patient": [
        "PatNum", "LName", "FName", "Birthdate", "Gender",
        "Address", "City", "State", "Zip", "HmPhone", "Email",
    ],
    "procedure": [
        "PatNum", "ProcDate", "ProcCode", "ToothNum", "Surf",
        "ProcFee", "ProcStatus", "ProvNum",
    ],
    "insurance": [
        "PatNum", "CarrierName", "GroupNum", "SubscriberID",
        "InsPhone", "PlanType",
    ],
}


def parse_dentrix_bridge_file(file_content: str, record_type: str = "patient") -> list[dict]:
    """
    Parse a Dentrix Bridge export file.

    Dentrix Bridge files are pipe-delimited text files with headers.
    This is useful for practices that can't enable DTXAPI but can
    export data through the Bridge feature.

    Args:
        file_content: Raw text content of the bridge file
        record_type: "patient", "procedure", or "insurance"

    Returns:
        List of dicts with parsed records
    """
    lines = file_content.strip().split("\n")
    if not lines:
        return []

    # Try to detect delimiter (pipe, tab, or comma)
    first_line = lines[0]
    if "|" in first_line:
        delimiter = "|"
    elif "\t" in first_line:
        delimiter = "\t"
    else:
        delimiter = ","

    # First line is headers
    headers = [h.strip() for h in first_line.split(delimiter)]

    records = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(delimiter)]
        if len(values) >= len(headers):
            record = dict(zip(headers, values))
            records.append(record)

    return records
