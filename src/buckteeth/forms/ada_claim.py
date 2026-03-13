from dataclasses import dataclass, field
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


@dataclass
class ProcedureLineItem:
    line_number: int
    cdt_code: str
    tooth_number: str
    surfaces: str
    description: str
    fee: float


@dataclass
class ClaimFormData:
    # Patient info
    patient_name: str
    patient_dob: str
    patient_address: str
    patient_gender: str
    # Subscriber info
    subscriber_name: str
    subscriber_id: str
    group_number: str
    # Payer info
    payer_name: str
    payer_address: str
    # Provider info
    provider_name: str
    provider_npi: str
    provider_license: str
    provider_address: str
    provider_tax_id: str
    # Claim info
    date_of_service: str
    procedures: list[ProcedureLineItem] = field(default_factory=list)
    total_fee: float = 0.0
    preauth_number: str | None = None


class ADAClaimFormGenerator:
    """Generates ADA Dental Claim Form PDFs."""

    def generate(self, data: ClaimFormData) -> bytes:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 0.75 * inch, "ADA Dental Claim Form")

        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, height - 1.0 * inch,
                            "Standard form for dental insurance claim submission")

        y = height - 1.5 * inch

        # Payer Information
        y = self._draw_section(c, "INSURANCE COMPANY / DENTAL BENEFIT PLAN", y, [
            ("Payer Name", data.payer_name),
            ("Payer Address", data.payer_address),
        ])

        # Patient Information
        y = self._draw_section(c, "PATIENT INFORMATION", y - 0.2 * inch, [
            ("Patient Name", data.patient_name),
            ("Date of Birth", data.patient_dob),
            ("Gender", data.patient_gender),
            ("Address", data.patient_address),
        ])

        # Subscriber Information
        y = self._draw_section(c, "SUBSCRIBER INFORMATION", y - 0.2 * inch, [
            ("Subscriber Name", data.subscriber_name),
            ("Subscriber ID", data.subscriber_id),
            ("Group Number", data.group_number),
        ])

        # Provider Information
        y = self._draw_section(c, "BILLING DENTIST", y - 0.2 * inch, [
            ("Provider Name", data.provider_name),
            ("NPI", data.provider_npi),
            ("License #", data.provider_license),
            ("Tax ID", data.provider_tax_id),
            ("Address", data.provider_address),
        ])

        if data.preauth_number:
            y = self._draw_section(c, "PRE-AUTHORIZATION", y - 0.2 * inch, [
                ("Pre-Authorization #", data.preauth_number),
            ])

        # Procedures table
        y -= 0.3 * inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y, "PROCEDURES")
        y -= 0.2 * inch

        # Table header
        c.setFont("Helvetica-Bold", 8)
        headers = [
            (0.5, "#"), (1.0, "Date"), (2.0, "CDT Code"),
            (2.8, "Tooth"), (3.5, "Surface"), (4.2, "Description"),
        ]
        for col_x, header in headers:
            c.drawString(col_x * inch, y, header)
        c.drawRightString(7.5 * inch, y, "Fee")
        y -= 0.05 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.15 * inch

        # Procedure lines
        c.setFont("Helvetica", 8)
        for proc in data.procedures:
            c.drawString(0.5 * inch, y, str(proc.line_number))
            c.drawString(1.0 * inch, y, data.date_of_service)
            c.drawString(2.0 * inch, y, proc.cdt_code)
            c.drawString(2.8 * inch, y, proc.tooth_number)
            c.drawString(3.5 * inch, y, proc.surfaces)
            c.drawString(4.2 * inch, y, proc.description[:30])
            c.drawRightString(7.5 * inch, y, f"${proc.fee:,.2f}")
            y -= 0.2 * inch

        # Total
        y -= 0.1 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.2 * inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(4.2 * inch, y, "TOTAL FEE:")
        c.drawRightString(7.5 * inch, y, f"${data.total_fee:,.2f}")

        c.save()
        return buffer.getvalue()

    @staticmethod
    def _draw_section(c, title, y, fields):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.5 * inch, y, title)
        y -= 0.05 * inch
        c.line(0.5 * inch, y, 7.5 * inch, y)
        y -= 0.18 * inch

        c.setFont("Helvetica", 9)
        for label, value in fields:
            c.drawString(0.5 * inch, y, f"{label}:")
            c.drawString(2.2 * inch, y, str(value))
            y -= 0.18 * inch

        return y
