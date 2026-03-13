import pytest
from buckteeth.forms.ada_claim import ADAClaimFormGenerator, ClaimFormData, ProcedureLineItem


@pytest.fixture
def generator():
    return ADAClaimFormGenerator()


@pytest.fixture
def sample_claim_data():
    return ClaimFormData(
        patient_name="Jane Doe",
        patient_dob="01/15/1990",
        patient_address="123 Main St, Los Angeles, CA 90001",
        patient_gender="F",
        subscriber_name="Jane Doe",
        subscriber_id="SUB123",
        group_number="GRP456",
        payer_name="Delta Dental",
        payer_address="PO Box 997330, Sacramento, CA 95899",
        provider_name="Dr. John Smith, DDS",
        provider_npi="1234567890",
        provider_license="CA-12345",
        provider_address="456 Dental Ave, Los Angeles, CA 90002",
        provider_tax_id="12-3456789",
        date_of_service="03/12/2026",
        procedures=[
            ProcedureLineItem(
                line_number=1,
                cdt_code="D2740",
                tooth_number="30",
                surfaces="",
                description="Crown - porcelain/ceramic",
                fee=1200.00,
            ),
        ],
        total_fee=1200.00,
    )


def test_generate_pdf(generator, sample_claim_data):
    pdf_bytes = generator.generate(sample_claim_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"  # Valid PDF header


def test_generate_pdf_multiple_procedures(generator, sample_claim_data):
    sample_claim_data.procedures.append(
        ProcedureLineItem(
            line_number=2,
            cdt_code="D2950",
            tooth_number="30",
            surfaces="",
            description="Core buildup",
            fee=350.00,
        )
    )
    sample_claim_data.total_fee = 1550.00
    pdf_bytes = generator.generate(sample_claim_data)
    assert pdf_bytes[:4] == b"%PDF"
