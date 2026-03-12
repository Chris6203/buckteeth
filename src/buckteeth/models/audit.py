import uuid

from sqlalchemy import String, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from buckteeth.models.base import TenantScopedBase


class AuditLog(TenantScopedBase):
    __tablename__ = "audit_logs"

    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid())
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
