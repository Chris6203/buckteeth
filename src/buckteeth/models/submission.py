import uuid

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from buckteeth.models.base import TenantScopedBase


class SubmissionRecord(TenantScopedBase):
    __tablename__ = "submission_records"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(30))  # clearinghouse, pms, paper
    clearinghouse_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="submitted"
    )  # submitted, accepted, rejected, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True
    )


class ERARecord(TenantScopedBase):
    __tablename__ = "era_records"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"), nullable=False
    )
    payer_name: Mapped[str] = mapped_column(String(200))
    payer_id: Mapped[str] = mapped_column(String(50))
    payment_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_responsibility: Mapped[float | None] = mapped_column(Float, nullable=True)
    adjustment_reason_codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="paid"
    )  # paid, denied, partial, adjusted
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
