# Phase 6: PMS Adapter Layer

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the practice management system (PMS) adapter layer — abstract interface, mock adapter for testing, Open Dental REST API adapter stub, CSV file-based import/export adapter, and PMS sync API endpoints for pulling patients/encounters and pushing claims.

**Architecture:** New `pms` module under `src/buckteeth/`. Abstract `PMSAdapter` interface with concrete implementations. Mock adapter for dev/testing. Open Dental adapter as a real integration stub. CSV adapter for file-based import/export (Tier 3). API endpoints for triggering PMS sync operations.

**Tech Stack:** Same as prior phases

---

## Chunk 1: PMS Adapter Interface & Mock

### Task 1: PMS adapter interface and data schemas

**Files:**
- Create: `src/buckteeth/pms/__init__.py`
- Create: `src/buckteeth/pms/schemas.py`
- Create: `src/buckteeth/pms/adapters.py`
- Create: `tests/pms/__init__.py`
- Create: `tests/pms/test_adapters.py`

- [ ] **Step 1: Write PMS schemas**

Create `src/buckteeth/pms/schemas.py`:

```python
from dataclasses import dataclass, field
from datetime import date


@dataclass
class PMSPatient:
    external_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    primary_payer_name: str | None = None
    primary_payer_id: str | None = None
    primary_subscriber_id: str | None = None
    primary_group_number: str | None = None


@dataclass
class PMSProcedure:
    code: str
    description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    fee: float = 0.0
    status: str = "completed"  # completed, planned, in_progress


@dataclass
class PMSEncounter:
    external_id: str
    patient_external_id: str
    provider_name: str
    date_of_service: str
    procedures: list[PMSProcedure] = field(default_factory=list)
    notes: str | None = None


@dataclass
class PMSTreatmentHistory:
    patient_external_id: str
    encounters: list[PMSEncounter] = field(default_factory=list)


@dataclass
class PMSClaimResult:
    external_claim_id: str
    status: str  # accepted, rejected, error
    message: str | None = None


@dataclass
class PMSFeeSchedule:
    payer_id: str
    fees: dict[str, float] = field(default_factory=dict)  # cdt_code -> fee


@dataclass
class PMSConnectionStatus:
    connected: bool
    pms_name: str
    version: str | None = None
    last_sync: str | None = None
    error: str | None = None
```

- [ ] **Step 2: Write tests for adapter interface and mock**

Create `tests/pms/test_adapters.py`:

```python
import pytest
from buckteeth.pms.adapters import MockPMSAdapter
from buckteeth.pms.schemas import (
    PMSPatient, PMSEncounter, PMSTreatmentHistory,
    PMSClaimResult, PMSFeeSchedule, PMSConnectionStatus,
)


@pytest.fixture
def adapter():
    return MockPMSAdapter()


async def test_authenticate(adapter):
    status = await adapter.authenticate({"api_key": "test"})
    assert isinstance(status, PMSConnectionStatus)
    assert status.connected is True
    assert status.pms_name == "MockPMS"


async def test_pull_patients(adapter):
    patients = await adapter.pull_patients()
    assert len(patients) > 0
    assert all(isinstance(p, PMSPatient) for p in patients)
    assert patients[0].first_name is not None


async def test_pull_patients_with_filter(adapter):
    patients = await adapter.pull_patients(last_name="Smith")
    assert len(patients) >= 1
    assert all(p.last_name == "Smith" for p in patients)


async def test_pull_encounter(adapter):
    encounter = await adapter.pull_encounter(
        patient_external_id="PAT-001",
        date_of_service="2026-03-12",
    )
    assert isinstance(encounter, PMSEncounter)
    assert len(encounter.procedures) > 0


async def test_pull_treatment_history(adapter):
    history = await adapter.pull_treatment_history("PAT-001")
    assert isinstance(history, PMSTreatmentHistory)
    assert len(history.encounters) > 0


async def test_push_claim(adapter):
    result = await adapter.push_coded_claim(
        patient_external_id="PAT-001",
        claim_data={
            "procedures": [{"code": "D1110", "fee": 150.00}],
            "payer_id": "DD001",
        },
    )
    assert isinstance(result, PMSClaimResult)
    assert result.status == "accepted"


async def test_get_fee_schedule(adapter):
    schedule = await adapter.get_fee_schedule("DD001")
    assert isinstance(schedule, PMSFeeSchedule)
    assert len(schedule.fees) > 0
    assert "D1110" in schedule.fees
```

- [ ] **Step 3: Implement adapter interface and mock**

Create `src/buckteeth/pms/adapters.py`:

```python
import uuid
from abc import ABC, abstractmethod

from buckteeth.pms.schemas import (
    PMSPatient, PMSEncounter, PMSProcedure, PMSTreatmentHistory,
    PMSClaimResult, PMSFeeSchedule, PMSConnectionStatus,
)


class PMSAdapter(ABC):
    """Abstract interface for practice management system integrations."""

    @abstractmethod
    async def authenticate(self, credentials: dict) -> PMSConnectionStatus: ...

    @abstractmethod
    async def pull_patients(self, **filters) -> list[PMSPatient]: ...

    @abstractmethod
    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None: ...

    @abstractmethod
    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory: ...

    @abstractmethod
    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult: ...

    @abstractmethod
    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule: ...


# Sample data for the mock adapter
_MOCK_PATIENTS = [
    PMSPatient(
        external_id="PAT-001", first_name="Jane", last_name="Smith",
        date_of_birth="1985-03-15", gender="F",
        phone="555-0101", email="jane.smith@email.com",
        address="123 Oak St, Los Angeles, CA 90001",
        primary_payer_name="Delta Dental", primary_payer_id="DD001",
        primary_subscriber_id="SUB-001", primary_group_number="GRP-100",
    ),
    PMSPatient(
        external_id="PAT-002", first_name="John", last_name="Doe",
        date_of_birth="1972-07-22", gender="M",
        phone="555-0102", email="john.doe@email.com",
        address="456 Elm St, Los Angeles, CA 90002",
        primary_payer_name="MetLife Dental", primary_payer_id="ML001",
        primary_subscriber_id="SUB-002", primary_group_number="GRP-200",
    ),
    PMSPatient(
        external_id="PAT-003", first_name="Maria", last_name="Smith",
        date_of_birth="1990-11-08", gender="F",
        phone="555-0103",
        primary_payer_name="Cigna Dental", primary_payer_id="CG001",
        primary_subscriber_id="SUB-003", primary_group_number="GRP-300",
    ),
]

_MOCK_ENCOUNTERS = [
    PMSEncounter(
        external_id="ENC-001", patient_external_id="PAT-001",
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        procedures=[
            PMSProcedure(code="D1110", description="Prophylaxis - adult", fee=150.00),
            PMSProcedure(code="D0120", description="Periodic oral evaluation", fee=65.00),
            PMSProcedure(code="D0274", description="Bitewings - four films", fee=85.00),
        ],
        notes="Routine 6-month recall. Healthy dentition, no new findings.",
    ),
    PMSEncounter(
        external_id="ENC-002", patient_external_id="PAT-001",
        provider_name="Dr. Smith", date_of_service="2025-09-10",
        procedures=[
            PMSProcedure(code="D2740", description="Crown - porcelain/ceramic",
                         tooth_number="30", fee=1200.00),
            PMSProcedure(code="D2950", description="Core buildup",
                         tooth_number="30", fee=350.00),
        ],
        notes="Crown prep #30. Large MOD amalgam failing with recurrent decay.",
    ),
    PMSEncounter(
        external_id="ENC-003", patient_external_id="PAT-002",
        provider_name="Dr. Jones", date_of_service="2026-03-12",
        procedures=[
            PMSProcedure(code="D4341", description="SRP - 4+ teeth per quadrant",
                         tooth_number="", surfaces="", fee=275.00),
        ],
        notes="Periodontal therapy UR quadrant. Pockets 5-7mm.",
    ),
]

_MOCK_FEE_SCHEDULE = {
    "D0120": 65.00, "D0150": 95.00, "D0210": 150.00, "D0274": 85.00,
    "D1110": 150.00, "D1120": 95.00, "D2140": 195.00, "D2150": 235.00,
    "D2160": 280.00, "D2161": 320.00, "D2330": 175.00, "D2331": 210.00,
    "D2332": 250.00, "D2335": 290.00, "D2391": 215.00, "D2392": 260.00,
    "D2393": 300.00, "D2394": 340.00, "D2740": 1200.00, "D2750": 1100.00,
    "D2950": 350.00, "D3310": 800.00, "D3320": 950.00, "D3330": 1100.00,
    "D4341": 275.00, "D4342": 200.00, "D7140": 225.00, "D7210": 350.00,
}


class MockPMSAdapter(PMSAdapter):
    """Mock PMS adapter for development and testing."""

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        return PMSConnectionStatus(
            connected=True,
            pms_name="MockPMS",
            version="1.0.0",
            last_sync="2026-03-12T10:00:00Z",
        )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        patients = _MOCK_PATIENTS
        if "last_name" in filters:
            patients = [p for p in patients if p.last_name == filters["last_name"]]
        if "external_id" in filters:
            patients = [p for p in patients if p.external_id == filters["external_id"]]
        return patients

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        for enc in _MOCK_ENCOUNTERS:
            if (enc.patient_external_id == patient_external_id
                    and enc.date_of_service == date_of_service):
                return enc
        return None

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        encounters = [e for e in _MOCK_ENCOUNTERS
                      if e.patient_external_id == patient_external_id]
        return PMSTreatmentHistory(
            patient_external_id=patient_external_id,
            encounters=encounters,
        )

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        return PMSClaimResult(
            external_claim_id=f"CLM-{uuid.uuid4().hex[:8].upper()}",
            status="accepted",
            message="Claim accepted by MockPMS",
        )

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        return PMSFeeSchedule(payer_id=payer_id, fees=_MOCK_FEE_SCHEDULE)
```

- [ ] **Step 4: Run tests, commit**

### Task 2: Open Dental adapter stub

**Files:**
- Create: `src/buckteeth/pms/open_dental.py`
- Create: `tests/pms/test_open_dental.py`

- [ ] **Step 1: Write tests**

Create `tests/pms/test_open_dental.py`:

```python
import pytest
from buckteeth.pms.open_dental import OpenDentalAdapter
from buckteeth.pms.schemas import PMSConnectionStatus


@pytest.fixture
def adapter():
    return OpenDentalAdapter(base_url="http://localhost:30222/api/v1", api_key="test-key")


async def test_authenticate_raises_not_implemented(adapter):
    """Open Dental adapter methods raise NotImplementedError until real API is configured."""
    with pytest.raises(NotImplementedError, match="Open Dental"):
        await adapter.authenticate({})


def test_adapter_stores_config(adapter):
    assert adapter._base_url == "http://localhost:30222/api/v1"
    assert adapter._api_key == "test-key"
```

- [ ] **Step 2: Implement Open Dental adapter stub**

Create `src/buckteeth/pms/open_dental.py`:

```python
"""Open Dental PMS Adapter.

Open Dental exposes a REST API (typically at localhost:30222/api/v1 on the
office server). This adapter implements the PMSAdapter interface against
the Open Dental API.

Documentation: https://www.opendental.com/site/apispecification.html

Requires:
- Open Dental 22.1+ with API enabled
- API key generated from Open Dental Setup > Advanced Setup > API
"""

from buckteeth.pms.adapters import PMSAdapter
from buckteeth.pms.schemas import (
    PMSClaimResult, PMSConnectionStatus, PMSEncounter,
    PMSFeeSchedule, PMSPatient, PMSTreatmentHistory,
)


class OpenDentalAdapter(PMSAdapter):
    """Open Dental REST API adapter (Tier 1 integration)."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    async def authenticate(self, credentials: dict) -> PMSConnectionStatus:
        # TODO: GET {base_url}/patients?limit=1 to verify connectivity
        raise NotImplementedError(
            "Open Dental integration pending API access. "
            "Configure base_url and api_key in settings."
        )

    async def pull_patients(self, **filters) -> list[PMSPatient]:
        # TODO: GET {base_url}/patients with query params
        raise NotImplementedError("Open Dental pull_patients pending implementation")

    async def pull_encounter(
        self, patient_external_id: str, date_of_service: str,
    ) -> PMSEncounter | None:
        # TODO: GET {base_url}/procedurelogs?PatNum={id}&ProcDate={date}
        raise NotImplementedError("Open Dental pull_encounter pending implementation")

    async def pull_treatment_history(
        self, patient_external_id: str,
    ) -> PMSTreatmentHistory:
        # TODO: GET {base_url}/procedurelogs?PatNum={id}
        raise NotImplementedError("Open Dental pull_treatment_history pending implementation")

    async def push_coded_claim(
        self, patient_external_id: str, claim_data: dict,
    ) -> PMSClaimResult:
        # TODO: POST {base_url}/claims with claim body
        raise NotImplementedError("Open Dental push_coded_claim pending implementation")

    async def get_fee_schedule(self, payer_id: str) -> PMSFeeSchedule:
        # TODO: GET {base_url}/feescheds?InsPayPlanNum={id}
        raise NotImplementedError("Open Dental get_fee_schedule pending implementation")
```

- [ ] **Step 3: Run tests, commit**

### Task 3: CSV file-based import/export adapter

**Files:**
- Create: `src/buckteeth/pms/csv_adapter.py`
- Create: `tests/pms/test_csv_adapter.py`

- [ ] **Step 1: Write tests**

Create `tests/pms/test_csv_adapter.py`:

```python
import csv
import os
import tempfile

import pytest
from buckteeth.pms.csv_adapter import CSVAdapter
from buckteeth.pms.schemas import PMSPatient, PMSEncounter, PMSConnectionStatus


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def adapter_with_data(temp_dir):
    # Write sample patients CSV
    patients_path = os.path.join(temp_dir, "patients.csv")
    with open(patients_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "external_id", "first_name", "last_name", "date_of_birth",
            "gender", "payer_name", "payer_id", "subscriber_id", "group_number",
        ])
        writer.writeheader()
        writer.writerow({
            "external_id": "CSV-001", "first_name": "Alice",
            "last_name": "Johnson", "date_of_birth": "1988-05-20",
            "gender": "F", "payer_name": "Delta Dental",
            "payer_id": "DD001", "subscriber_id": "SUB-100",
            "group_number": "GRP-500",
        })

    # Write sample encounters CSV
    encounters_path = os.path.join(temp_dir, "encounters.csv")
    with open(encounters_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "external_id", "patient_external_id", "provider_name",
            "date_of_service", "cdt_code", "description",
            "tooth_number", "surfaces", "fee", "notes",
        ])
        writer.writeheader()
        writer.writerow({
            "external_id": "ENC-CSV-001", "patient_external_id": "CSV-001",
            "provider_name": "Dr. Brown", "date_of_service": "2026-03-12",
            "cdt_code": "D1110", "description": "Prophylaxis - adult",
            "tooth_number": "", "surfaces": "", "fee": "150.00",
            "notes": "Routine cleaning",
        })

    return CSVAdapter(data_dir=temp_dir)


async def test_csv_authenticate(adapter_with_data):
    status = await adapter_with_data.authenticate({})
    assert isinstance(status, PMSConnectionStatus)
    assert status.connected is True
    assert status.pms_name == "CSV Import/Export"


async def test_csv_pull_patients(adapter_with_data):
    patients = await adapter_with_data.pull_patients()
    assert len(patients) == 1
    assert patients[0].first_name == "Alice"
    assert patients[0].primary_payer_name == "Delta Dental"


async def test_csv_pull_encounter(adapter_with_data):
    enc = await adapter_with_data.pull_encounter("CSV-001", "2026-03-12")
    assert enc is not None
    assert len(enc.procedures) == 1
    assert enc.procedures[0].code == "D1110"


async def test_csv_export_claim(adapter_with_data, temp_dir):
    result = await adapter_with_data.push_coded_claim(
        patient_external_id="CSV-001",
        claim_data={
            "procedures": [{"code": "D1110", "description": "Prophy", "fee": 150.00}],
            "payer_id": "DD001",
            "date_of_service": "2026-03-12",
        },
    )
    assert result.status == "accepted"

    # Verify export file was written
    export_path = os.path.join(temp_dir, "claims_export.csv")
    assert os.path.exists(export_path)
```

- [ ] **Step 2: Implement CSV adapter**

Create `src/buckteeth/pms/csv_adapter.py`:

```python
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
```

- [ ] **Step 3: Run tests, commit**

---

## Chunk 2: PMS Sync API Endpoints

### Task 4: PMS sync API endpoints

**Files:**
- Create: `src/buckteeth/api/pms.py`
- Create: `tests/api/test_pms.py`
- Modify: `src/buckteeth/api/schemas.py` (add PMS schemas)
- Modify: `src/buckteeth/main.py` (register PMS router)

- [ ] **Step 1: Add PMS API schemas to `src/buckteeth/api/schemas.py`**

Append after the existing denial schemas section:

```python
# ── PMS Integration ─────────────────────────────────────────────────────


class PMSConnectionResponse(BaseModel):
    connected: bool
    pms_name: str
    version: str | None = None
    last_sync: str | None = None


class PMSPatientResponse(BaseModel):
    external_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    primary_payer_name: str | None = None
    primary_subscriber_id: str | None = None


class PMSEncounterResponse(BaseModel):
    external_id: str
    patient_external_id: str
    provider_name: str
    date_of_service: str
    procedure_count: int
    notes: str | None = None


class PMSImportPatientRequest(BaseModel):
    external_id: str


class PMSImportEncounterRequest(BaseModel):
    patient_external_id: str
    date_of_service: str
```

- [ ] **Step 2: Implement PMS router**

Create `src/buckteeth/api/pms.py`:

Router prefix: `/v1/pms`

Endpoints:
- `GET /status` — Check PMS connection status (uses MockPMSAdapter)
- `GET /patients` — List patients from PMS (optional `last_name` query param)
- `GET /patients/{external_id}/encounters` — Get treatment history from PMS
- `POST /import-patient` (201) — Import a patient from PMS into Buckteeth's DB. Pulls patient data from PMS, creates Patient + InsurancePlan records.
- `POST /import-encounter` (201) — Import an encounter from PMS. Pulls encounter from PMS, creates ClinicalEncounter + ClinicalProcedure records.

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.api.schemas import (
    PMSConnectionResponse, PMSEncounterResponse, PMSImportEncounterRequest,
    PMSImportPatientRequest, PMSPatientResponse, EncounterResponse, PatientResponse,
)
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.patient import Patient, InsurancePlan
from buckteeth.pms.adapters import MockPMSAdapter

router = APIRouter(prefix="/v1/pms", tags=["pms"])


def _get_adapter():
    return MockPMSAdapter()


@router.get("/status", response_model=PMSConnectionResponse)
async def check_pms_status():
    adapter = _get_adapter()
    status = await adapter.authenticate({})
    return PMSConnectionResponse(
        connected=status.connected,
        pms_name=status.pms_name,
        version=status.version,
        last_sync=status.last_sync,
    )


@router.get("/patients", response_model=list[PMSPatientResponse])
async def list_pms_patients(
    last_name: str | None = Query(default=None),
):
    adapter = _get_adapter()
    filters = {}
    if last_name:
        filters["last_name"] = last_name
    patients = await adapter.pull_patients(**filters)
    return [
        PMSPatientResponse(
            external_id=p.external_id,
            first_name=p.first_name,
            last_name=p.last_name,
            date_of_birth=p.date_of_birth,
            gender=p.gender,
            primary_payer_name=p.primary_payer_name,
            primary_subscriber_id=p.primary_subscriber_id,
        )
        for p in patients
    ]


@router.get("/patients/{external_id}/encounters", response_model=list[PMSEncounterResponse])
async def list_pms_encounters(external_id: str):
    adapter = _get_adapter()
    history = await adapter.pull_treatment_history(external_id)
    return [
        PMSEncounterResponse(
            external_id=e.external_id,
            patient_external_id=e.patient_external_id,
            provider_name=e.provider_name,
            date_of_service=e.date_of_service,
            procedure_count=len(e.procedures),
            notes=e.notes,
        )
        for e in history.encounters
    ]


@router.post("/import-patient", response_model=PatientResponse, status_code=201)
async def import_patient_from_pms(
    body: PMSImportPatientRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    adapter = _get_adapter()
    pms_patients = await adapter.pull_patients(external_id=body.external_id)
    if not pms_patients:
        raise HTTPException(status_code=404, detail="Patient not found in PMS")
    pms_patient = pms_patients[0]

    patient = Patient(
        tenant_id=tenant_id,
        first_name=pms_patient.first_name,
        last_name=pms_patient.last_name,
        date_of_birth=pms_patient.date_of_birth,
        gender=pms_patient.gender,
    )
    session.add(patient)
    await session.flush()

    if pms_patient.primary_payer_name:
        plan = InsurancePlan(
            tenant_id=tenant_id,
            patient_id=patient.id,
            payer_name=pms_patient.primary_payer_name,
            payer_id=pms_patient.primary_payer_id or "",
            subscriber_id=pms_patient.primary_subscriber_id or "",
            group_number=pms_patient.primary_group_number or "",
            plan_type="primary",
        )
        session.add(plan)
        await session.flush()

    await session.refresh(patient)
    return patient


@router.post("/import-encounter", response_model=EncounterResponse, status_code=201)
async def import_encounter_from_pms(
    body: PMSImportEncounterRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    adapter = _get_adapter()
    pms_encounter = await adapter.pull_encounter(
        body.patient_external_id, body.date_of_service,
    )
    if pms_encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found in PMS")

    # For import, we need a patient in our system. Use a placeholder approach.
    pms_patients = await adapter.pull_patients(external_id=body.patient_external_id)
    if not pms_patients:
        raise HTTPException(status_code=404, detail="Patient not found in PMS")
    pms_patient = pms_patients[0]

    # Create or lookup patient
    patient = Patient(
        tenant_id=tenant_id,
        first_name=pms_patient.first_name,
        last_name=pms_patient.last_name,
        date_of_birth=pms_patient.date_of_birth,
        gender=pms_patient.gender,
    )
    session.add(patient)
    await session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=patient.id,
        provider_name=pms_encounter.provider_name,
        date_of_service=pms_encounter.date_of_service,
        raw_notes=pms_encounter.notes or "",
        raw_input_type="pms_import",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in pms_encounter.procedures:
        clinical_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers=[int(proc.tooth_number)] if proc.tooth_number and proc.tooth_number.isdigit() else None,
            surfaces=list(proc.surfaces) if proc.surfaces else None,
            quadrant=None,
            diagnosis=None,
        )
        session.add(clinical_proc)

    await session.flush()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()
```

- [ ] **Step 3: Register router in main.py**

Add to imports and include:
```python
from buckteeth.api.pms import router as pms_router
app.include_router(pms_router)
```

- [ ] **Step 4: Write tests**

Create `tests/api/test_pms.py`:

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from buckteeth.database import get_db
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


async def test_pms_status(client):
    response = await client.get("/v1/pms/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["pms_name"] == "MockPMS"


async def test_list_pms_patients(client):
    response = await client.get("/v1/pms/patients")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # Mock has 3 patients


async def test_list_pms_patients_filter(client):
    response = await client.get("/v1/pms/patients?last_name=Smith")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # Jane Smith + Maria Smith
    assert all(p["last_name"] == "Smith" for p in data)


async def test_list_pms_encounters(client):
    response = await client.get("/v1/pms/patients/PAT-001/encounters")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2  # PAT-001 has 2 encounters


async def test_import_patient(client):
    response = await client.post(
        "/v1/pms/import-patient",
        json={"external_id": "PAT-001"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"


async def test_import_encounter(client):
    response = await client.post(
        "/v1/pms/import-encounter",
        json={
            "patient_external_id": "PAT-001",
            "date_of_service": "2026-03-12",
        },
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_input_type"] == "pms_import"
    assert len(data["procedures"]) == 3  # 3 procedures in mock ENC-001


async def test_import_patient_not_found(client):
    response = await client.post(
        "/v1/pms/import-patient",
        json={"external_id": "NONEXISTENT"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 404
```

- [ ] **Step 5: Run all tests, commit**

---

## Phase 6 Summary

Phase 6 delivers:
- Abstract `PMSAdapter` interface defining the standard PMS integration contract
- `MockPMSAdapter` with realistic dental office data (3 patients, 3 encounters, fee schedule)
- `OpenDentalAdapter` stub (Tier 1) ready for real API implementation
- `CSVAdapter` (Tier 3) for file-based import/export
- PMS data schemas (PMSPatient, PMSEncounter, PMSTreatmentHistory, PMSClaimResult, PMSFeeSchedule)
- REST API for PMS operations (status check, patient/encounter listing, import from PMS)
- Foundation for Tier 2 bridge agent (Dentrix/Eaglesoft) integration
