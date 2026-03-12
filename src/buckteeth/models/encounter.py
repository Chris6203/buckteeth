import uuid

from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from buckteeth.models.base import TenantScopedBase


class ClinicalEncounter(TenantScopedBase):
    __tablename__ = "clinical_encounters"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(200))
    date_of_service: Mapped[str] = mapped_column(String(10))
    raw_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input_type: Mapped[str] = mapped_column(String(20))  # text, voice, image, structured
    status: Mapped[str] = mapped_column(String(20), default="pending")

    procedures: Mapped[list["ClinicalProcedure"]] = relationship(back_populates="encounter")


class ClinicalProcedure(TenantScopedBase):
    __tablename__ = "clinical_procedures"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinical_encounters.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text)
    tooth_numbers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    surfaces: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)

    encounter: Mapped["ClinicalEncounter"] = relationship(back_populates="procedures")
