from pydantic import BaseModel


class ParsedProcedure(BaseModel):
    description: str
    tooth_numbers: list[int] | None = None
    surfaces: list[str] | None = None
    quadrant: str | None = None
    diagnosis: str | None = None


class ParsedEncounter(BaseModel):
    procedures: list[ParsedProcedure]
    notes: str | None = None
