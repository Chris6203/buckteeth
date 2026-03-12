from pydantic import BaseModel


class CodeSuggestion(BaseModel):
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    confidence_score: int  # 0-100
    ai_reasoning: str
    flags: list[str] = []
    icd10_codes: list[str] = []


class CodingResult(BaseModel):
    suggestions: list[CodeSuggestion]
    encounter_notes: str | None = None
