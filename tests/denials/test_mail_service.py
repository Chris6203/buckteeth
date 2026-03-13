import pytest
from buckteeth.denials.mail_service import MockMailService, MailResult


@pytest.fixture
def mail_service():
    return MockMailService()


async def test_send_letter(mail_service):
    result = await mail_service.send_letter(
        to_name="California Department of Insurance",
        to_address_line1="300 Capitol Mall, Suite 1700",
        to_city="Sacramento",
        to_state="CA",
        to_zip="95814",
        from_name="Dr. Smith DDS",
        from_address_line1="456 Dental Ave",
        from_city="Los Angeles",
        from_state="CA",
        from_zip="90002",
        letter_html="<p>Dear Commissioner...</p>",
    )
    assert isinstance(result, MailResult)
    assert result.mail_id is not None
    assert result.status == "created"


async def test_check_mail_status(mail_service):
    result = await mail_service.send_letter(
        to_name="Test", to_address_line1="123 Test St",
        to_city="Test", to_state="CA", to_zip="90000",
        from_name="Test", from_address_line1="456 Test St",
        from_city="Test", from_state="CA", from_zip="90000",
        letter_html="<p>Test</p>",
    )
    status = await mail_service.check_status(result.mail_id)
    assert status in ("created", "in_transit", "delivered")
