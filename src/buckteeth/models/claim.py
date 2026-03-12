import uuid

from sqlalchemy import Float, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from buckteeth.models.base import TenantScopedBase


class Claim(TenantScopedBase):
    __tablename__ = "claims"

    coded_encounter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coded_encounters.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(200))
    date_of_service: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # Primary payer
    primary_payer_name: Mapped[str] = mapped_column(String(200))
    primary_payer_id: Mapped[str] = mapped_column(String(50))
    primary_subscriber_id: Mapped[str] = mapped_column(String(100))
    primary_group_number: Mapped[str] = mapped_column(String(100))

    # Secondary payer
    secondary_payer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    secondary_payer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_subscriber_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    secondary_group_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Preauthorization
    preauth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    preauth_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preauth_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Fees
    total_fee_submitted: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_fee_allowed: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_fee_paid: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    procedures: Mapped[list["ClaimProcedure"]] = relationship(back_populates="claim")
    narratives: Mapped[list["ClaimNarrative"]] = relationship(back_populates="claim")
    attachments: Mapped[list["ClaimAttachment"]] = relationship(back_populates="claim")


class ClaimProcedure(TenantScopedBase):
    __tablename__ = "claim_procedures"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"), nullable=False
    )
    coded_procedure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("coded_procedures.id"), nullable=False
    )
    cdt_code: Mapped[str] = mapped_column(String(10))
    cdt_description: Mapped[str] = mapped_column(Text)
    tooth_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    surfaces: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fee_submitted: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_allowed: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_paid: Mapped[float | None] = mapped_column(Float, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="procedures")


class ClaimNarrative(TenantScopedBase):
    __tablename__ = "claim_narratives"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"), nullable=False
    )
    cdt_code: Mapped[str] = mapped_column(String(10))
    narrative_text: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[str] = mapped_column(String(20))
    payer_tailored: Mapped[bool] = mapped_column(Boolean, default=False)

    claim: Mapped["Claim"] = relationship(back_populates="narratives")


class ClaimAttachment(TenantScopedBase):
    __tablename__ = "claim_attachments"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="attachments")
