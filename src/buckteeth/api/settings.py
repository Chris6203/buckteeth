import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/settings", tags=["settings"])

SETTINGS_FILE = os.environ.get("SETTINGS_FILE", "/opt/buckteeth/practice_settings.json")


class PracticeSettings(BaseModel):
    practice_name: str = ""
    provider_name: str = ""
    provider_credentials: str = "DDS"
    npi: str = ""
    tax_id: str = ""
    taxonomy_code: str = "1223G0001X"
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    phone: str = ""
    email: str = ""
    clearinghouse_name: str = ""
    clearinghouse_account_id: str = ""
    clearinghouse_environment: str = "sandbox"
    fee_schedule: dict[str, float] = {}


@router.get("", response_model=PracticeSettings)
async def get_settings():
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        return PracticeSettings(**data)
    except (FileNotFoundError, json.JSONDecodeError):
        return PracticeSettings()


@router.put("", response_model=PracticeSettings)
async def update_settings(body: PracticeSettings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(body.model_dump(), f, indent=2)
    return body
