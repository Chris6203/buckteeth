import uuid
from sqlalchemy import String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from buckteeth.models.base import TenantScopedBase


class DenialRecord(TenantScopedBase):
    __tablename__ = "denial_records"

    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), nullable=False)
    denial_reason_code: Mapped[str] = mapped_column(String(20))  # CARC/RARC code
    denial_reason_description: Mapped[str] = mapped_column(Text)
    denied_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    payer_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))  # denied, appealed, overturned, upheld

    appeals: Mapped[list["AppealDocument"]] = relationship(back_populates="denial")
    commissioner_letters: Mapped[list["CommissionerLetter"]] = relationship(back_populates="denial")


class AppealDocument(TenantScopedBase):
    __tablename__ = "appeal_documents"

    denial_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("denial_records.id"), nullable=False)
    appeal_text: Mapped[str] = mapped_column(Text)
    case_law_citations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supporting_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(20))  # ai, human
    status: Mapped[str] = mapped_column(String(20))  # draft, sent, overturned, upheld
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)

    denial: Mapped["DenialRecord"] = relationship(back_populates="appeals")


class CommissionerLetter(TenantScopedBase):
    __tablename__ = "commissioner_letters"

    denial_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("denial_records.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(2))
    commissioner_name: Mapped[str] = mapped_column(String(300))
    commissioner_address: Mapped[str] = mapped_column(Text)
    letter_text: Mapped[str] = mapped_column(Text)
    case_law_citations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mail_status: Mapped[str] = mapped_column(String(20))  # pending, sent, delivered, returned
    mail_tracking_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(10))  # auto, manual
    lob_letter_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    denial: Mapped["DenialRecord"] = relationship(back_populates="commissioner_letters")
