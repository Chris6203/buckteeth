import uuid

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from buckteeth.models.base import TenantScopedBase


class Patient(TenantScopedBase):
    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[str] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(10))

    insurance_plans: Mapped[list["InsurancePlan"]] = relationship(back_populates="patient")


class InsurancePlan(TenantScopedBase):
    __tablename__ = "insurance_plans"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), nullable=False)
    payer_name: Mapped[str] = mapped_column(String(200))
    payer_id: Mapped[str] = mapped_column(String(50))
    subscriber_id: Mapped[str] = mapped_column(String(100))
    group_number: Mapped[str] = mapped_column(String(100))
    plan_type: Mapped[str] = mapped_column(String(20))  # primary, secondary

    patient: Mapped["Patient"] = relationship(back_populates="insurance_plans")
