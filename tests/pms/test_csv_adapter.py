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
