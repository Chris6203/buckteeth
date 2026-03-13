"""CSV-based PMS adapter for file import/export (Tier 3).

Reads patient and encounter data from CSV files and exports claims
as CSV. Useful for PMS systems without APIs.

Expected files:
- patients.csv: external_id, first_name, last_name, date_of_birth, gender,
                 payer_name, payer_id, subscriber_id, group_number
- encounters.csv: external_id, patient_external_id, provider_name,
                  date_of_service, cdt_code, description,
                  tooth_number, surfaces, fee, notes
"""

import csv
import os
import uuid
from collections import defaultdict

from buckteeth.pms.adapters import PMSAdapter
from buckteeth.pms.schemas import (
    PMSClaimResult, PMSConnectionStatus, PMSEncounter, PMSFeeSchedule,
    PMSPatient, PMSProcedure, PMSTreatmentHistory,
)


class CSVAdapter(PMSAdapter):
    """File-based PMS adapter using CSV import/export."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        patients_exists = os.path.exists(os.path.join(self._data_dir, "patients.csv"))
        return PMSConnectionStatus(
            connected=patients_exists,
            pms_name="CSV Import/Export",
            version="1.0",
        )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        path = os.path.join(self._data_dir, "patients.csv")
        if not os.path.exists(path):
            return []

        patients = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                patient = PMSPatient(
                    external_id=row["external_id"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    date_of_birth=row["date_of_birth"],
                    gender=row["gender"],
                    primary_payer_name=row.get("payer_name"),
                    primary_payer_id=row.get("payer_id"),
                    primary_subscriber_id=row.get("subscriber_id"),
                    primary_group_number=row.get("group_number"),
                )
                if "last_name" in filters and patient.last_name != filters["last_name"]:
                    continue
                patients.append(patient)
        return patients

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        path = os.path.join(self._data_dir, "encounters.csv")
        if not os.path.exists(path):
            return None

        procedures = []
        encounter_id = None
        provider = None
        notes = None

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["patient_external_id"] == patient_external_id
                        and row["date_of_service"] == date_of_service):
                    encounter_id = row["external_id"]
                    provider = row["provider_name"]
                    notes = row.get("notes")
                    procedures.append(PMSProcedure(
                        code=row["cdt_code"],
                        description=row["description"],
                        tooth_number=row.get("tooth_number") or None,
                        surfaces=row.get("surfaces") or None,
                        fee=float(row.get("fee", 0)),
                    ))

        if not procedures:
            return None

        return PMSEncounter(
            external_id=encounter_id or f"CSV-{uuid.uuid4().hex[:8]}",
            patient_external_id=patient_external_id,
            provider_name=provider or "Unknown",
            date_of_service=date_of_service,
            procedures=procedures,
            notes=notes,
        )

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        path = os.path.join(self._data_dir, "encounters.csv")
        if not os.path.exists(path):
            return PMSTreatmentHistory(
                patient_external_id=patient_external_id, encounters=[]
            )

        encounters_by_date: dict[str, list] = defaultdict(list)
        encounter_meta: dict[str, dict] = {}

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["patient_external_id"] == patient_external_id:
                    dos = row["date_of_service"]
                    encounters_by_date[dos].append(PMSProcedure(
                        code=row["cdt_code"],
                        description=row["description"],
                        tooth_number=row.get("tooth_number") or None,
                        surfaces=row.get("surfaces") or None,
                        fee=float(row.get("fee", 0)),
                    ))
                    encounter_meta[dos] = {
                        "external_id": row["external_id"],
                        "provider_name": row["provider_name"],
                        "notes": row.get("notes"),
                    }

        encounters = []
        for dos, procs in encounters_by_date.items():
            meta = encounter_meta[dos]
            encounters.append(PMSEncounter(
                external_id=meta["external_id"],
                patient_external_id=patient_external_id,
                provider_name=meta["provider_name"],
                date_of_service=dos,
                procedures=procs,
                notes=meta.get("notes"),
            ))

        return PMSTreatmentHistory(
            patient_external_id=patient_external_id,
            encounters=encounters,
        )

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        export_path = os.path.join(self._data_dir, "claims_export.csv")
        file_exists = os.path.exists(export_path)

        claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"

        with open(export_path, "a", newline="") as f:
            fieldnames = [
                "claim_id", "patient_external_id", "payer_id",
                "date_of_service", "cdt_code", "description", "fee",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            for proc in claim_data.get("procedures", []):
                writer.writerow({
                    "claim_id": claim_id,
                    "patient_external_id": patient_external_id,
                    "payer_id": claim_data.get("payer_id", ""),
                    "date_of_service": claim_data.get("date_of_service", ""),
                    "cdt_code": proc.get("code", ""),
                    "description": proc.get("description", ""),
                    "fee": proc.get("fee", 0),
                })

        return PMSClaimResult(
            external_claim_id=claim_id,
            status="accepted",
            message="Claim exported to CSV",
        )

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        return PMSFeeSchedule(payer_id=payer_id, fees={})
