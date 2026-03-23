import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from buckteeth.api.deps import get_session, get_tenant_id
from buckteeth.config import settings
from buckteeth.denials.action_plan import generate_action_plan
from buckteeth.denials.document_verifier import DocumentVerifier
from buckteeth.api.schemas import (
    AppealDocumentResponse,
    CommissionerLetterAPIResponse,
    CreateDenialRequest,
    DenialResponse,
    GenerateAppealRequest,
    SendCommissionerLetterRequest,
)
from buckteeth.denials.appeal_generator import AppealGenerator
from buckteeth.denials.commissioner import CommissionerLetterGenerator
from buckteeth.denials.mail_service import MockMailService
from buckteeth.denials.schemas import (
    AppealRequest as AppealGenRequest,
    CommissionerLetterRequest as CommLetterGenRequest,
)
from buckteeth.models.claim import Claim, ClaimProcedure
from buckteeth.models.denial import AppealDocument, CommissionerLetter, DenialRecord
from buckteeth.models.patient import Patient

# Configurable per-tenant in production; module-level flag for now
AUTO_SEND_COMMISSIONER_LETTER = False

router = APIRouter(prefix="/v1/denials", tags=["denials"])


@router.post("", response_model=DenialResponse, status_code=201)
async def create_denial(
    body: CreateDenialRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Load and verify claim exists
    result = await session.execute(
        select(Claim).where(
            Claim.id == body.claim_id,
            Claim.tenant_id == tenant_id,
        )
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Create denial record
    denial = DenialRecord(
        tenant_id=tenant_id,
        claim_id=body.claim_id,
        denial_reason_code=body.denial_reason_code,
        denial_reason_description=body.denial_reason_description,
        denied_amount=body.denied_amount,
        payer_name=body.payer_name,
        status="denied",
    )
    session.add(denial)

    # Update claim status
    claim.status = "denied"

    await session.flush()
    await session.refresh(denial)
    return denial


@router.get("", response_model=list[DenialResponse])
async def list_denials(
    status: Optional[str] = Query(default=None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(DenialRecord).where(DenialRecord.tenant_id == tenant_id)
    if status is not None:
        stmt = stmt.where(DenialRecord.status == status)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/{denial_id}", response_model=DenialResponse)
async def get_denial(
    denial_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    denial = result.scalar_one_or_none()
    if denial is None:
        raise HTTPException(status_code=404, detail="Denial not found")
    return denial


@router.get("/{denial_id}/action-plan")
async def get_denial_action_plan(
    denial_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific action plan for resolving this denial."""
    result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    denial = result.scalar_one_or_none()
    if denial is None:
        raise HTTPException(status_code=404, detail="Denial not found")

    # Get the CDT code from the linked claim
    cdt_code = ""
    if denial.claim_id:
        claim_result = await session.execute(
            select(Claim).options(selectinload(Claim.procedures)).where(Claim.id == denial.claim_id)
        )
        claim = claim_result.scalar_one_or_none()
        if claim and claim.procedures:
            cdt_code = claim.procedures[0].cdt_code

    plan = generate_action_plan(
        denial_reason_code=denial.denial_reason_code,
        denial_reason_description=denial.denial_reason_description,
        payer_name=denial.payer_name,
        cdt_code=cdt_code,
        denied_amount=denial.denied_amount or 0,
    )
    return plan.to_dict()


@router.post("/{denial_id}/generate-appeal", response_model=AppealDocumentResponse, status_code=201)
async def generate_appeal(
    denial_id: uuid.UUID,
    body: GenerateAppealRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Load denial
    result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    denial = result.scalar_one_or_none()
    if denial is None:
        raise HTTPException(status_code=404, detail="Denial not found")

    # Load claim with procedures
    claim_result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(Claim.id == denial.claim_id)
    )
    claim = claim_result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Load patient
    patient_result = await session.execute(
        select(Patient).where(Patient.id == claim.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get CDT code from first procedure or use fallback
    cdt_code = "D0000"
    procedure_description = "Dental procedure"
    if claim.procedures:
        cdt_code = claim.procedures[0].cdt_code
        procedure_description = claim.procedures[0].cdt_description

    # Build appeal request
    appeal_request = AppealGenRequest(
        denial_reason_code=denial.denial_reason_code,
        denial_reason_description=denial.denial_reason_description,
        denied_amount=denial.denied_amount or 0.0,
        payer_name=denial.payer_name,
        cdt_code=cdt_code,
        procedure_description=procedure_description,
        clinical_notes=body.clinical_notes,
        patient_name=f"{patient.first_name} {patient.last_name}",
        date_of_service=claim.date_of_service,
        provider_name=claim.provider_name,
        state=body.state,
    )

    # Generate appeal via AI
    appeal_response = await AppealGenerator(api_key=settings.anthropic_api_key).generate_appeal(appeal_request)

    # Save AppealDocument to DB
    appeal_doc = AppealDocument(
        tenant_id=tenant_id,
        denial_id=denial_id,
        appeal_text=appeal_response.appeal_text,
        case_law_citations=appeal_response.case_law_citations,
        supporting_evidence={"key_arguments": appeal_response.key_arguments,
                             "recommended_attachments": appeal_response.recommended_attachments},
        generated_by="ai",
        status="draft",
    )
    session.add(appeal_doc)

    # Update denial status
    denial.status = "appealed"

    await session.flush()
    await session.refresh(appeal_doc)

    # Auto-send commissioner letter if configured
    if AUTO_SEND_COMMISSIONER_LETTER:
        comm_request = CommLetterGenRequest(
            denial_reason_code=denial.denial_reason_code,
            denial_reason_description=denial.denial_reason_description,
            denied_amount=denial.denied_amount or 0.0,
            payer_name=denial.payer_name,
            patient_name=f"{patient.first_name} {patient.last_name}",
            patient_address="",  # not available in appeal request
            provider_name=claim.provider_name,
            provider_address="",
            date_of_service=claim.date_of_service,
            cdt_code=cdt_code,
            procedure_description=procedure_description,
            clinical_notes=body.clinical_notes,
            state=body.state,
            appeal_already_filed=True,
        )
        comm_response = await CommissionerLetterGenerator(api_key=settings.anthropic_api_key).generate(comm_request)
        mail_service = MockMailService()
        mail_result = await mail_service.send_letter(
            to_name=comm_response.commissioner_name,
            to_address_line1=comm_response.commissioner_address,
            to_city="", to_state=body.state, to_zip="",
            from_name=claim.provider_name,
            from_address_line1="", from_city="", from_state=body.state, from_zip="",
            letter_html=comm_response.letter_text,
        )
        commissioner_letter = CommissionerLetter(
            tenant_id=tenant_id,
            denial_id=denial_id,
            patient_id=patient.id,
            state=body.state,
            commissioner_name=comm_response.commissioner_name,
            commissioner_address=comm_response.commissioner_address,
            letter_text=comm_response.letter_text,
            case_law_citations=comm_response.case_law_citations,
            mail_status=mail_result.status,
            mail_tracking_id=mail_result.mail_id,
            trigger_type="auto",
            lob_letter_id=mail_result.mail_id,
        )
        session.add(commissioner_letter)
        await session.flush()

    return appeal_doc


@router.post("/{denial_id}/send-commissioner-letter", response_model=CommissionerLetterAPIResponse, status_code=201)
async def send_commissioner_letter(
    denial_id: uuid.UUID,
    body: SendCommissionerLetterRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Load denial
    result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    denial = result.scalar_one_or_none()
    if denial is None:
        raise HTTPException(status_code=404, detail="Denial not found")

    # Load claim with procedures
    claim_result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.procedures))
        .where(Claim.id == denial.claim_id)
    )
    claim = claim_result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Load patient
    patient_result = await session.execute(
        select(Patient).where(Patient.id == claim.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get CDT code from first procedure or use fallback
    cdt_code = "D0000"
    procedure_description = "Dental procedure"
    if claim.procedures:
        cdt_code = claim.procedures[0].cdt_code
        procedure_description = claim.procedures[0].cdt_description

    # Build commissioner letter request
    letter_request = CommLetterGenRequest(
        denial_reason_code=denial.denial_reason_code,
        denial_reason_description=denial.denial_reason_description,
        denied_amount=denial.denied_amount or 0.0,
        payer_name=denial.payer_name,
        patient_name=f"{patient.first_name} {patient.last_name}",
        patient_address=body.patient_address,
        provider_name=claim.provider_name,
        provider_address=body.provider_address,
        date_of_service=claim.date_of_service,
        cdt_code=cdt_code,
        procedure_description=procedure_description,
        clinical_notes=body.clinical_notes,
        state=body.state,
        appeal_already_filed=True,
    )

    # Generate commissioner letter via AI
    letter_response = await CommissionerLetterGenerator(api_key=settings.anthropic_api_key).generate(letter_request)

    # Send via mail service
    mail_service = MockMailService()
    mail_result = await mail_service.send_letter(
        to_name=letter_response.commissioner_name,
        to_address_line1=letter_response.commissioner_address,
        to_city="",
        to_state=body.state,
        to_zip="",
        from_name=claim.provider_name,
        from_address_line1=body.provider_address,
        from_city="",
        from_state=body.state,
        from_zip="",
        letter_html=letter_response.letter_text,
    )

    # Save CommissionerLetter to DB
    commissioner_letter = CommissionerLetter(
        tenant_id=tenant_id,
        denial_id=denial_id,
        patient_id=patient.id,
        state=body.state,
        commissioner_name=letter_response.commissioner_name,
        commissioner_address=letter_response.commissioner_address,
        letter_text=letter_response.letter_text,
        case_law_citations=letter_response.case_law_citations,
        mail_status=mail_result.status,
        mail_tracking_id=mail_result.mail_id,
        trigger_type="manual",
        lob_letter_id=mail_result.mail_id,
    )
    session.add(commissioner_letter)

    await session.flush()
    await session.refresh(commissioner_letter)
    return commissioner_letter


@router.get("/{denial_id}/commissioner-letters", response_model=list[CommissionerLetterAPIResponse])
async def list_commissioner_letters(
    denial_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Verify denial exists
    denial_result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    denial = denial_result.scalar_one_or_none()
    if denial is None:
        raise HTTPException(status_code=404, detail="Denial not found")

    result = await session.execute(
        select(CommissionerLetter).where(
            CommissionerLetter.denial_id == denial_id,
            CommissionerLetter.tenant_id == tenant_id,
        )
    )
    return result.scalars().all()


# ── Denial Attachments ────────────────────────────────────────────────

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/opt/buckteeth/uploads/denials")

DOCUMENT_TYPES = [
    "periapical_xray",
    "bitewing_xray",
    "panoramic_xray",
    "intraoral_photo",
    "perio_charting",
    "clinical_narrative",
    "eob",
    "treatment_plan",
    "specialist_letter",
    "prior_claim",
    "other",
]

DOCUMENT_TYPE_LABELS = {
    "periapical_xray": "Periapical X-ray",
    "bitewing_xray": "Bitewing X-ray",
    "panoramic_xray": "Panoramic X-ray",
    "intraoral_photo": "Intraoral Photo",
    "perio_charting": "Periodontal Charting",
    "clinical_narrative": "Clinical Narrative",
    "eob": "Explanation of Benefits (EOB)",
    "treatment_plan": "Treatment Plan",
    "specialist_letter": "Specialist Letter",
    "prior_claim": "Prior Claim Copy",
    "other": "Other Document",
}


@router.post("/{denial_id}/attachments")
async def upload_denial_attachment(
    denial_id: uuid.UUID,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    description: str = Form(default=""),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Upload a document to attach to a denial for appeal purposes."""
    result = await session.execute(
        select(DenialRecord).where(
            DenialRecord.id == denial_id,
            DenialRecord.tenant_id == tenant_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Denial not found")

    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type. Must be one of: {', '.join(DOCUMENT_TYPES)}",
        )

    file_id = uuid.uuid4()
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Verify document with AI (non-blocking — still saves even if verification fails)
    verification = None
    if settings.anthropic_api_key and (file.content_type or "").startswith("image/"):
        try:
            verifier = DocumentVerifier(api_key=settings.anthropic_api_key)
            verification = await verifier.verify(
                file_data=content,
                media_type=file.content_type or "image/jpeg",
                claimed_type=document_type,
            )
        except Exception:
            pass

    await session.execute(
        text("""
            INSERT INTO denial_attachments (id, tenant_id, denial_id, file_name, file_type, file_path, document_type, description)
            VALUES (:id, :tenant_id, :denial_id, :file_name, :file_type, :file_path, :document_type, :description)
        """),
        {
            "id": file_id,
            "tenant_id": str(tenant_id),
            "denial_id": str(denial_id),
            "file_name": file.filename or "unknown",
            "file_type": file.content_type or "application/octet-stream",
            "file_path": file_path,
            "document_type": document_type,
            "description": description,
        },
    )
    await session.commit()

    return {
        "id": str(file_id),
        "file_name": file.filename,
        "document_type": document_type,
        "description": description,
        "verification": verification,
    }


@router.get("/{denial_id}/attachments")
async def list_denial_attachments(
    denial_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """List all documents attached to a denial."""
    result = await session.execute(
        text("""
            SELECT id, file_name, file_type, document_type, description, uploaded_at
            FROM denial_attachments
            WHERE denial_id = :denial_id AND tenant_id = :tenant_id
            ORDER BY uploaded_at DESC
        """),
        {"denial_id": str(denial_id), "tenant_id": str(tenant_id)},
    )
    return [
        {
            "id": str(r[0]),
            "file_name": r[1],
            "file_type": r[2],
            "document_type": r[3],
            "document_type_label": DOCUMENT_TYPE_LABELS.get(r[3], r[3]),
            "description": r[4],
            "uploaded_at": r[5].isoformat() if r[5] else None,
        }
        for r in result.fetchall()
    ]


@router.delete("/{denial_id}/attachments/{attachment_id}")
async def delete_denial_attachment(
    denial_id: uuid.UUID,
    attachment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Remove an attachment from a denial."""
    result = await session.execute(
        text("""
            SELECT file_path FROM denial_attachments
            WHERE id = :id AND denial_id = :denial_id AND tenant_id = :tenant_id
        """),
        {"id": str(attachment_id), "denial_id": str(denial_id), "tenant_id": str(tenant_id)},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        os.remove(row[0])
    except OSError:
        pass

    await session.execute(
        text("DELETE FROM denial_attachments WHERE id = :id"),
        {"id": str(attachment_id)},
    )
    await session.commit()
    return {"deleted": True}
