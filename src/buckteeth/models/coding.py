import uuid

from sqlalchemy import String, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from buckteeth.models.base import TenantScopedBase


class CodedEncounter(TenantScopedBase):
    __tablename__ = "coded_encounters"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id"), nullable=False, unique=True
    )
    review_status: Mapped[str] = mapped_column(String(20), default="pending")

    coded_procedures: Mapped[list["CodedProcedure"]] = relationship(
        back_populates="coded_encounter"
    )


class CodedProcedure(TenantScopedBase):
    __tablename__ = "coded_procedures"

    coded_encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coded_encounters.id"), nullable=False
    )
    clinical_procedure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_procedures.id"), nullable=False
    )
    cdt_code: Mapped[str] = mapped_column(String(10))
    cdt_description: Mapped[str] = mapped_column(Text)
    tooth_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    surfaces: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer)
    ai_reasoning: Mapped[str] = mapped_column(Text)
    flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    icd10_codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_cdt_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    coded_encounter: Mapped["CodedEncounter"] = relationship(back_populates="coded_procedures")
