#!/usr/bin/env python3
"""
Seed script for Buckteeth dental app demo data.

Creates realistic dental office data including patients, insurance plans,
clinical encounters, coded procedures, claims, submissions, and denials.

Usage:
    python scripts/seed_demo.py

Reads DATABASE_URL from /opt/buckteeth/.env and converts to sync psycopg2 format.
"""

import json
import os
import re
import uuid

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def get_database_url() -> str:
    """Read DATABASE_URL from /opt/buckteeth/.env and convert to sync format."""
    env_path = "/opt/buckteeth/.env"
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1]
                # Convert from asyncpg to psycopg2 format
                url = re.sub(r"postgresql\+asyncpg://", "postgresql://", url)
                return url
    raise RuntimeError("DATABASE_URL not found in /opt/buckteeth/.env")


# ---------------------------------------------------------------------------
# Deterministic UUIDs for referential integrity
# ---------------------------------------------------------------------------

def make_id(namespace: str, index: int) -> str:
    return str(uuid.uuid5(uuid.UUID(TENANT_ID), f"{namespace}-{index}"))


# Patient IDs
PAT = [make_id("patient", i) for i in range(6)]

# Insurance plan IDs
INS = [make_id("insurance", i) for i in range(6)]

# Clinical encounter IDs
ENC = [make_id("encounter", i) for i in range(5)]

# Clinical procedure IDs
CPROC = [make_id("clinproc", i) for i in range(12)]

# Coded encounter IDs
CENC = [make_id("codedenc", i) for i in range(4)]

# Coded procedure IDs
CDPROC = [make_id("codedproc", i) for i in range(10)]

# Claim IDs
CLM = [make_id("claim", i) for i in range(4)]

# Claim procedure IDs
CLMP = [make_id("claimproc", i) for i in range(8)]

# Claim narrative IDs
CLMN = [make_id("claimnarr", i) for i in range(2)]

# Submission record IDs
SUB = [make_id("submission", i) for i in range(2)]

# Denial record IDs
DEN = [make_id("denial", i) for i in range(2)]


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

PATIENTS = [
    {
        "id": PAT[0], "tenant_id": TENANT_ID,
        "first_name": "Maria", "last_name": "Gonzalez",
        "date_of_birth": "1985-03-14", "gender": "female",
    },
    {
        "id": PAT[1], "tenant_id": TENANT_ID,
        "first_name": "James", "last_name": "Thompson",
        "date_of_birth": "1972-11-28", "gender": "male",
    },
    {
        "id": PAT[2], "tenant_id": TENANT_ID,
        "first_name": "Aisha", "last_name": "Patel",
        "date_of_birth": "1990-07-02", "gender": "female",
    },
    {
        "id": PAT[3], "tenant_id": TENANT_ID,
        "first_name": "Robert", "last_name": "Chen",
        "date_of_birth": "1968-01-19", "gender": "male",
    },
    {
        "id": PAT[4], "tenant_id": TENANT_ID,
        "first_name": "Linda", "last_name": "Williams",
        "date_of_birth": "1955-09-07", "gender": "female",
    },
    {
        "id": PAT[5], "tenant_id": TENANT_ID,
        "first_name": "Derek", "last_name": "Johnson",
        "date_of_birth": "1998-12-30", "gender": "male",
    },
]

INSURANCE_PLANS = [
    {
        "id": INS[0], "tenant_id": TENANT_ID, "patient_id": PAT[0],
        "payer_name": "Delta Dental Premier", "payer_id": "DELTA01",
        "subscriber_id": "DD-889-2041573", "group_number": "GRP-44821",
        "plan_type": "primary",
    },
    {
        "id": INS[1], "tenant_id": TENANT_ID, "patient_id": PAT[1],
        "payer_name": "MetLife Dental PPO", "payer_id": "METLF01",
        "subscriber_id": "ML-472-9183620", "group_number": "GRP-71056",
        "plan_type": "primary",
    },
    {
        "id": INS[2], "tenant_id": TENANT_ID, "patient_id": PAT[2],
        "payer_name": "Cigna Dental DHMO", "payer_id": "CIGNA01",
        "subscriber_id": "CG-601-3847291", "group_number": "GRP-93204",
        "plan_type": "primary",
    },
    {
        "id": INS[3], "tenant_id": TENANT_ID, "patient_id": PAT[3],
        "payer_name": "Aetna Dental PPO", "payer_id": "AETNA01",
        "subscriber_id": "AE-315-7620489", "group_number": "GRP-28517",
        "plan_type": "primary",
    },
    {
        "id": INS[4], "tenant_id": TENANT_ID, "patient_id": PAT[4],
        "payer_name": "Guardian Dental Guard Preferred", "payer_id": "GUARD01",
        "subscriber_id": "GD-758-4092163", "group_number": "GRP-60389",
        "plan_type": "primary",
    },
    {
        "id": INS[5], "tenant_id": TENANT_ID, "patient_id": PAT[5],
        "payer_name": "Delta Dental PPO", "payer_id": "DELTA02",
        "subscriber_id": "DD-924-5831047", "group_number": "GRP-15742",
        "plan_type": "primary",
    },
]

CLINICAL_ENCOUNTERS = [
    {
        "id": ENC[0], "tenant_id": TENANT_ID, "patient_id": PAT[0],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-10",
        "raw_notes": (
            "Patient presents for routine prophylaxis and periodic oral evaluation. "
            "No new complaints. Mild calculus buildup on lingual of lower anteriors. "
            "Gingival tissue appears healthy with no bleeding on probing. "
            "Four bitewing radiographs taken for caries detection. "
            "All quadrants scaled and polished. Fluoride varnish applied. "
            "Patient educated on proper flossing technique."
        ),
        "raw_input_type": "text",
        "status": "completed",
    },
    {
        "id": ENC[1], "tenant_id": TENANT_ID, "patient_id": PAT[1],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-12",
        "raw_notes": (
            "Patient presents with fractured porcelain on tooth #30 (existing PFM crown). "
            "Clinical exam reveals fracture extending to metal substructure. "
            "Crown is non-restorable - full replacement recommended. "
            "Tooth is vital, no periapical pathology on radiograph. "
            "Impressions taken for PFM crown. Shade A2 selected. "
            "Temporary crown fabricated and cemented with TempBond. "
            "Patient to return in 2 weeks for permanent cementation."
        ),
        "raw_input_type": "text",
        "status": "completed",
    },
    {
        "id": ENC[2], "tenant_id": TENANT_ID, "patient_id": PAT[2],
        "provider_name": "Dr. Michael Torres, DMD",
        "date_of_service": "2026-03-15",
        "raw_notes": (
            "Patient referred for scaling and root planing. Generalized moderate "
            "chronic periodontitis with 4-6mm pockets in all quadrants. "
            "BOP positive in 60% of sites. Radiographic bone loss of 20-30% "
            "in posterior regions. SRP performed on upper right and lower right "
            "quadrants today under local anesthesia (2% lidocaine with 1:100k epi). "
            "Gross calculus removed with ultrasonic scaler, followed by hand "
            "instrumentation with Gracey curettes. Root surfaces planed smooth. "
            "Irrigation with 0.12% chlorhexidine. Patient scheduled for "
            "remaining quadrants next week."
        ),
        "raw_input_type": "text",
        "status": "completed",
    },
    {
        "id": ENC[3], "tenant_id": TENANT_ID, "patient_id": PAT[3],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-18",
        "raw_notes": (
            "Patient presents with chief complaint of sensitivity on upper left. "
            "Clinical exam reveals large carious lesion on #14 involving "
            "mesial-occlusal-distal surfaces. Vitality testing positive. "
            "No periapical radiolucency. Treatment: composite resin restoration "
            "(MOD) on tooth #14 under local anesthesia. Caries excavated, "
            "selective etch technique with universal adhesive (Scotchbond Universal). "
            "Composite placed in increments (3M Filtek Supreme, shade A3). "
            "Occlusion checked and adjusted. Patient tolerated procedure well."
        ),
        "raw_input_type": "text",
        "status": "completed",
    },
    {
        "id": ENC[4], "tenant_id": TENANT_ID, "patient_id": PAT[4],
        "provider_name": "Dr. Michael Torres, DMD",
        "date_of_service": "2026-03-20",
        "raw_notes": (
            "Patient presents for surgical extraction of #17 (upper left third molar). "
            "Tooth partially erupted, distoangular impaction. "
            "Periapical radiograph confirms full root formation with close "
            "proximity to maxillary sinus. Risks discussed and consent obtained. "
            "Local anesthesia: PSA and GP blocks with 2% lidocaine 1:100k epi. "
            "Full-thickness mucoperiosteal flap raised. Minimal bone removal "
            "with surgical handpiece. Tooth sectioned and delivered in two pieces. "
            "Socket irrigated, hemostasis achieved. Primary closure with "
            "3-0 chromic gut sutures. Post-op instructions and Rx for "
            "amoxicillin 500mg TID x 7 days and ibuprofen 600mg Q6H PRN provided."
        ),
        "raw_input_type": "text",
        "status": "completed",
    },
]

# Clinical procedures linked to encounters
CLINICAL_PROCEDURES = [
    # Encounter 0: Prophylaxis visit (Maria Gonzalez)
    {
        "id": CPROC[0], "tenant_id": TENANT_ID, "encounter_id": ENC[0],
        "description": "Periodic oral evaluation - established patient",
        "tooth_numbers": None, "surfaces": None, "quadrant": None,
        "diagnosis": "Routine dental maintenance, mild calculus",
    },
    {
        "id": CPROC[1], "tenant_id": TENANT_ID, "encounter_id": ENC[0],
        "description": "Prophylaxis - adult, scaling and polishing all quadrants",
        "tooth_numbers": None, "surfaces": None, "quadrant": None,
        "diagnosis": "Mild supragingival calculus, healthy gingiva",
    },
    {
        "id": CPROC[2], "tenant_id": TENANT_ID, "encounter_id": ENC[0],
        "description": "Four bitewing radiographs for caries detection",
        "tooth_numbers": None, "surfaces": None, "quadrant": None,
        "diagnosis": "Caries risk assessment - low risk",
    },
    # Encounter 1: Crown prep (James Thompson)
    {
        "id": CPROC[3], "tenant_id": TENANT_ID, "encounter_id": ENC[1],
        "description": "Crown preparation and temporization - porcelain fused to metal crown on tooth #30",
        "tooth_numbers": [30], "surfaces": None, "quadrant": None,
        "diagnosis": "Fractured PFM crown, non-restorable, tooth vital",
    },
    # Encounter 2: SRP (Aisha Patel)
    {
        "id": CPROC[4], "tenant_id": TENANT_ID, "encounter_id": ENC[2],
        "description": "Scaling and root planing - upper right quadrant, 4-6mm pockets",
        "tooth_numbers": None, "surfaces": None, "quadrant": "UR",
        "diagnosis": "Generalized moderate chronic periodontitis, BOP 60%, 20-30% bone loss",
    },
    {
        "id": CPROC[5], "tenant_id": TENANT_ID, "encounter_id": ENC[2],
        "description": "Scaling and root planing - lower right quadrant, 4-6mm pockets",
        "tooth_numbers": None, "surfaces": None, "quadrant": "LR",
        "diagnosis": "Generalized moderate chronic periodontitis, BOP 60%, 20-30% bone loss",
    },
    # Encounter 3: Composite filling (Robert Chen)
    {
        "id": CPROC[6], "tenant_id": TENANT_ID, "encounter_id": ENC[3],
        "description": "Composite resin restoration, three surfaces (MOD) on tooth #14",
        "tooth_numbers": [14], "surfaces": ["M", "O", "D"], "quadrant": "UL",
        "diagnosis": "Large carious lesion involving mesial-occlusal-distal, tooth vital",
    },
    # Encounter 4: Extraction (Linda Williams)
    {
        "id": CPROC[7], "tenant_id": TENANT_ID, "encounter_id": ENC[4],
        "description": "Surgical extraction of partially erupted, impacted third molar #17",
        "tooth_numbers": [17], "surfaces": None, "quadrant": "UL",
        "diagnosis": "Partially erupted distoangular impacted third molar, close to maxillary sinus",
    },
]

# Coded encounters (AI-coded versions of clinical encounters)
CODED_ENCOUNTERS = [
    {
        "id": CENC[0], "tenant_id": TENANT_ID, "encounter_id": ENC[0],
        "review_status": "approved",
    },
    {
        "id": CENC[1], "tenant_id": TENANT_ID, "encounter_id": ENC[1],
        "review_status": "approved",
    },
    {
        "id": CENC[2], "tenant_id": TENANT_ID, "encounter_id": ENC[2],
        "review_status": "approved",
    },
    {
        "id": CENC[3], "tenant_id": TENANT_ID, "encounter_id": ENC[3],
        "review_status": "pending",
    },
]

CODED_PROCEDURES = [
    # Coded encounter 0: Prophylaxis visit
    {
        "id": CDPROC[0], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[0], "clinical_procedure_id": CPROC[0],
        "cdt_code": "D0120",
        "cdt_description": "Periodic oral evaluation - established patient",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "confidence_score": 98,
        "ai_reasoning": (
            "Clinical notes describe a periodic evaluation for an established patient "
            "with no new chief complaint. D0120 is the appropriate code for routine "
            "periodic exams, distinct from D0150 (comprehensive) or D0180 (comprehensive "
            "periodontal). High confidence as the documentation clearly supports this code."
        ),
        "flags": None,
        "icd10_codes": ["Z01.20"],
        "override_reason": None, "original_cdt_code": None,
    },
    {
        "id": CDPROC[1], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[0], "clinical_procedure_id": CPROC[1],
        "cdt_code": "D1110",
        "cdt_description": "Prophylaxis - adult (14 years and older)",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "confidence_score": 97,
        "ai_reasoning": (
            "Documentation indicates scaling and polishing for an adult patient with "
            "mild calculus and healthy gingiva. D1110 is appropriate for adult prophylaxis "
            "in the absence of periodontal disease. Pocket depths and bleeding on probing "
            "are within normal limits, ruling out D4341/D4342 (SRP)."
        ),
        "flags": None,
        "icd10_codes": ["Z01.20", "K03.6"],
        "override_reason": None, "original_cdt_code": None,
    },
    {
        "id": CDPROC[2], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[0], "clinical_procedure_id": CPROC[2],
        "cdt_code": "D0274",
        "cdt_description": "Bitewings - four radiographic images",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "confidence_score": 99,
        "ai_reasoning": (
            "Clinical notes explicitly state four bitewing radiographs taken. "
            "D0274 is the correct code for four bitewing images. This is distinct from "
            "D0272 (two images) or D0273 (three images)."
        ),
        "flags": None,
        "icd10_codes": ["Z01.20"],
        "override_reason": None, "original_cdt_code": None,
    },
    # Coded encounter 1: Crown
    {
        "id": CDPROC[3], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[1], "clinical_procedure_id": CPROC[3],
        "cdt_code": "D2750",
        "cdt_description": "Crown - porcelain fused to high noble metal",
        "tooth_number": "30", "surfaces": None, "quadrant": None,
        "confidence_score": 92,
        "ai_reasoning": (
            "Notes indicate a PFM crown replacement for tooth #30 with fractured existing "
            "PFM crown. D2750 (porcelain fused to high noble metal) is selected based on the "
            "standard of care for posterior PFM crowns. Considered D2740 (porcelain/ceramic "
            "crown) but PFM is documented. Also considered D2752 (base metal) but high noble "
            "is the default unless otherwise specified. Slightly lower confidence due to the "
            "notes not specifying the metal type explicitly."
        ),
        "flags": ["verify_metal_type"],
        "icd10_codes": ["K08.539", "K02.9"],
        "override_reason": None, "original_cdt_code": None,
    },
    # Coded encounter 2: SRP
    {
        "id": CDPROC[4], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[2], "clinical_procedure_id": CPROC[4],
        "cdt_code": "D4341",
        "cdt_description": "Periodontal scaling and root planing - four or more teeth per quadrant",
        "tooth_number": None, "surfaces": None, "quadrant": "UR",
        "confidence_score": 96,
        "ai_reasoning": (
            "Documentation clearly describes SRP in the upper right quadrant for a patient "
            "with generalized moderate chronic periodontitis, 4-6mm pockets, and BOP in 60% "
            "of sites. D4341 is appropriate as four or more teeth are involved per quadrant. "
            "The 20-30% radiographic bone loss supports the periodontal diagnosis. "
            "Distinct from D4342 (1-3 teeth) and D1110 (prophylaxis without periodontal disease)."
        ),
        "flags": None,
        "icd10_codes": ["K05.319"],
        "override_reason": None, "original_cdt_code": None,
    },
    {
        "id": CDPROC[5], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[2], "clinical_procedure_id": CPROC[5],
        "cdt_code": "D4341",
        "cdt_description": "Periodontal scaling and root planing - four or more teeth per quadrant",
        "tooth_number": None, "surfaces": None, "quadrant": "LR",
        "confidence_score": 96,
        "ai_reasoning": (
            "Same clinical justification as UR quadrant. SRP performed in lower right "
            "quadrant for generalized moderate chronic periodontitis. Four or more teeth "
            "involved. Documentation supports medical necessity with 4-6mm probing depths "
            "and positive BOP."
        ),
        "flags": None,
        "icd10_codes": ["K05.319"],
        "override_reason": None, "original_cdt_code": None,
    },
    # Coded encounter 3: Composite filling
    {
        "id": CDPROC[6], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[3], "clinical_procedure_id": CPROC[6],
        "cdt_code": "D2393",
        "cdt_description": "Resin-based composite - three surfaces, posterior",
        "tooth_number": "14", "surfaces": "MOD", "quadrant": None,
        "confidence_score": 95,
        "ai_reasoning": (
            "Notes describe a composite resin restoration on tooth #14 involving mesial, "
            "occlusal, and distal surfaces. D2393 is the correct code for a three-surface "
            "posterior resin composite. Initially considered D2391 (one surface) and D2392 "
            "(two surfaces) but the MOD preparation clearly involves three surfaces. "
            "Tooth #14 (upper left first premolar) is a posterior tooth, confirming the "
            "posterior composite code series."
        ),
        "flags": None,
        "icd10_codes": ["K02.62"],
        "override_reason": None, "original_cdt_code": None,
    },
]

# Claims in various statuses
CLAIMS = [
    # Claim 0: Prophylaxis visit - accepted/paid
    {
        "id": CLM[0], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[0], "patient_id": PAT[0],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-10",
        "status": "accepted",
        "primary_payer_name": "Delta Dental Premier",
        "primary_payer_id": "DELTA01",
        "primary_subscriber_id": "DD-889-2041573",
        "primary_group_number": "GRP-44821",
        "secondary_payer_name": None, "secondary_payer_id": None,
        "secondary_subscriber_id": None, "secondary_group_number": None,
        "preauth_required": False, "preauth_number": None, "preauth_status": None,
        "total_fee_submitted": 412.00,
        "total_fee_allowed": 378.00,
        "total_fee_paid": 302.40,
    },
    # Claim 1: Crown - submitted, pending
    {
        "id": CLM[1], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[1], "patient_id": PAT[1],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-12",
        "status": "submitted",
        "primary_payer_name": "MetLife Dental PPO",
        "primary_payer_id": "METLF01",
        "primary_subscriber_id": "ML-472-9183620",
        "primary_group_number": "GRP-71056",
        "secondary_payer_name": None, "secondary_payer_id": None,
        "secondary_subscriber_id": None, "secondary_group_number": None,
        "preauth_required": True,
        "preauth_number": "PA-2026-038271",
        "preauth_status": "approved",
        "total_fee_submitted": 1285.00,
        "total_fee_allowed": None,
        "total_fee_paid": None,
    },
    # Claim 2: SRP - denied
    {
        "id": CLM[2], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[2], "patient_id": PAT[2],
        "provider_name": "Dr. Michael Torres, DMD",
        "date_of_service": "2026-03-15",
        "status": "denied",
        "primary_payer_name": "Cigna Dental DHMO",
        "primary_payer_id": "CIGNA01",
        "primary_subscriber_id": "CG-601-3847291",
        "primary_group_number": "GRP-93204",
        "secondary_payer_name": None, "secondary_payer_id": None,
        "secondary_subscriber_id": None, "secondary_group_number": None,
        "preauth_required": False, "preauth_number": None, "preauth_status": None,
        "total_fee_submitted": 560.00,
        "total_fee_allowed": 0.00,
        "total_fee_paid": 0.00,
    },
    # Claim 3: Composite filling - draft
    {
        "id": CLM[3], "tenant_id": TENANT_ID,
        "coded_encounter_id": CENC[3], "patient_id": PAT[3],
        "provider_name": "Dr. Sarah Mitchell, DDS",
        "date_of_service": "2026-03-18",
        "status": "draft",
        "primary_payer_name": "Aetna Dental PPO",
        "primary_payer_id": "AETNA01",
        "primary_subscriber_id": "AE-315-7620489",
        "primary_group_number": "GRP-28517",
        "secondary_payer_name": None, "secondary_payer_id": None,
        "secondary_subscriber_id": None, "secondary_group_number": None,
        "preauth_required": False, "preauth_number": None, "preauth_status": None,
        "total_fee_submitted": 325.00,
        "total_fee_allowed": None,
        "total_fee_paid": None,
    },
]

CLAIM_PROCEDURES = [
    # Claim 0 procedures (prophylaxis)
    {
        "id": CLMP[0], "tenant_id": TENANT_ID,
        "claim_id": CLM[0], "coded_procedure_id": CDPROC[0],
        "cdt_code": "D0120", "cdt_description": "Periodic oral evaluation - established patient",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "fee_submitted": 62.00, "fee_allowed": 55.00, "fee_paid": 44.00,
    },
    {
        "id": CLMP[1], "tenant_id": TENANT_ID,
        "claim_id": CLM[0], "coded_procedure_id": CDPROC[1],
        "cdt_code": "D1110", "cdt_description": "Prophylaxis - adult",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "fee_submitted": 135.00, "fee_allowed": 120.00, "fee_paid": 96.00,
    },
    {
        "id": CLMP[2], "tenant_id": TENANT_ID,
        "claim_id": CLM[0], "coded_procedure_id": CDPROC[2],
        "cdt_code": "D0274", "cdt_description": "Bitewings - four radiographic images",
        "tooth_number": None, "surfaces": None, "quadrant": None,
        "fee_submitted": 85.00, "fee_allowed": 78.00, "fee_paid": 62.40,
    },
    # Claim 1 procedures (crown)
    {
        "id": CLMP[3], "tenant_id": TENANT_ID,
        "claim_id": CLM[1], "coded_procedure_id": CDPROC[3],
        "cdt_code": "D2750",
        "cdt_description": "Crown - porcelain fused to high noble metal",
        "tooth_number": "30", "surfaces": None, "quadrant": None,
        "fee_submitted": 1285.00, "fee_allowed": None, "fee_paid": None,
    },
    # Claim 2 procedures (SRP)
    {
        "id": CLMP[4], "tenant_id": TENANT_ID,
        "claim_id": CLM[2], "coded_procedure_id": CDPROC[4],
        "cdt_code": "D4341",
        "cdt_description": "Periodontal scaling and root planing - four or more teeth per quadrant",
        "tooth_number": None, "surfaces": None, "quadrant": "UR",
        "fee_submitted": 280.00, "fee_allowed": 0.00, "fee_paid": 0.00,
    },
    {
        "id": CLMP[5], "tenant_id": TENANT_ID,
        "claim_id": CLM[2], "coded_procedure_id": CDPROC[5],
        "cdt_code": "D4341",
        "cdt_description": "Periodontal scaling and root planing - four or more teeth per quadrant",
        "tooth_number": None, "surfaces": None, "quadrant": "LR",
        "fee_submitted": 280.00, "fee_allowed": 0.00, "fee_paid": 0.00,
    },
    # Claim 3 procedures (composite)
    {
        "id": CLMP[6], "tenant_id": TENANT_ID,
        "claim_id": CLM[3], "coded_procedure_id": CDPROC[6],
        "cdt_code": "D2393",
        "cdt_description": "Resin-based composite - three surfaces, posterior",
        "tooth_number": "14", "surfaces": "MOD", "quadrant": None,
        "fee_submitted": 325.00, "fee_allowed": None, "fee_paid": None,
    },
]

CLAIM_NARRATIVES = [
    {
        "id": CLMN[0], "tenant_id": TENANT_ID,
        "claim_id": CLM[1], "cdt_code": "D2750",
        "narrative_text": (
            "Patient presented with a fractured porcelain fused to metal crown on tooth #30. "
            "Clinical examination revealed the fracture extends to the metal substructure, "
            "rendering the existing restoration non-restorable. The tooth remains vital with "
            "no periapical pathology evident on radiographic examination. A new porcelain "
            "fused to high noble metal crown is medically necessary to restore proper form, "
            "function, and esthetics. The existing crown has been in service for over 8 years. "
            "Impressions were taken and a temporary crown was placed pending lab fabrication."
        ),
        "generated_by": "ai",
        "payer_tailored": True,
    },
    {
        "id": CLMN[1], "tenant_id": TENANT_ID,
        "claim_id": CLM[2], "cdt_code": "D4341",
        "narrative_text": (
            "Patient presents with generalized moderate chronic periodontitis. Clinical "
            "findings include probing depths of 4-6mm in all quadrants, bleeding on probing "
            "at 60% of sites, and radiographic evidence of 20-30% horizontal bone loss in "
            "posterior regions. Scaling and root planing was performed in the upper right and "
            "lower right quadrants to remove subgingival calculus and bacterial deposits, "
            "and to plane the root surfaces for improved tissue adaptation. Ultrasonic "
            "instrumentation followed by hand scaling with Gracey curettes was employed. "
            "This treatment is medically necessary to arrest the progression of periodontal "
            "disease and prevent further attachment loss."
        ),
        "generated_by": "ai",
        "payer_tailored": True,
    },
]

SUBMISSION_RECORDS = [
    {
        "id": SUB[0], "tenant_id": TENANT_ID,
        "claim_id": CLM[0],
        "channel": "clearinghouse",
        "clearinghouse_name": "DentalXChange",
        "tracking_number": "DXC-2026-0310-78421",
        "confirmation_number": "CNF-DD-2026031045891",
        "status": "accepted",
        "error_message": None,
        "response_data": json.dumps({
            "accepted_at": "2026-03-11T14:23:00Z",
            "payer_claim_id": "DDC-2026-8847201",
            "estimated_payment_date": "2026-03-25",
        }),
        "idempotency_key": "idem-seed-claim0-sub0",
    },
    {
        "id": SUB[1], "tenant_id": TENANT_ID,
        "claim_id": CLM[1],
        "channel": "clearinghouse",
        "clearinghouse_name": "DentalXChange",
        "tracking_number": "DXC-2026-0312-94610",
        "confirmation_number": None,
        "status": "submitted",
        "error_message": None,
        "response_data": None,
        "idempotency_key": "idem-seed-claim1-sub1",
    },
]

DENIAL_RECORDS = [
    {
        "id": DEN[0], "tenant_id": TENANT_ID,
        "claim_id": CLM[2],
        "denial_reason_code": "N362",
        "denial_reason_description": (
            "Frequency limitation - scaling and root planing was performed within "
            "24 months of a previous SRP claim for the same quadrants. Per plan benefit "
            "limitations, D4341 is payable once per quadrant in a 24-month period."
        ),
        "denied_amount": 280.00,
        "payer_name": "Cigna Dental DHMO",
        "status": "denied",
    },
    {
        "id": DEN[1], "tenant_id": TENANT_ID,
        "claim_id": CLM[2],
        "denial_reason_code": "N523",
        "denial_reason_description": (
            "Missing pre-authorization. Per plan requirements, periodontal procedures "
            "including scaling and root planing (D4341, D4342) require prior authorization. "
            "No pre-authorization on file for this date of service."
        ),
        "denied_amount": 280.00,
        "payer_name": "Cigna Dental DHMO",
        "status": "appealed",
    },
]


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------

def insert_rows(cur, table: str, rows: list[dict]):
    """Insert a list of dicts into a table. Handles JSON serialization."""
    if not rows:
        return
    columns = list(rows[0].keys())
    col_names = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    for row in rows:
        values = []
        for col in columns:
            v = row[col]
            # Serialize dicts/lists to JSON strings for JSON columns
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            values.append(v)
        cur.execute(sql, values)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db_url = get_database_url()
    print(f"Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # Clean existing demo data for this tenant (in reverse FK order)
        tables_to_clean = [
            "commissioner_letters", "appeal_documents", "denial_records",
            "era_records", "submission_records",
            "claim_attachments", "claim_narratives", "claim_procedures", "claims",
            "coded_procedures", "coded_encounters",
            "clinical_procedures", "clinical_encounters",
            "insurance_plans", "patients",
            "audit_logs",
        ]
        for table in tables_to_clean:
            cur.execute(f"DELETE FROM {table} WHERE tenant_id = %s", (TENANT_ID,))
        print("Cleaned existing demo data for tenant.")

        # Insert in FK order
        print("Seeding patients...")
        insert_rows(cur, "patients", PATIENTS)

        print("Seeding insurance plans...")
        insert_rows(cur, "insurance_plans", INSURANCE_PLANS)

        print("Seeding clinical encounters...")
        insert_rows(cur, "clinical_encounters", CLINICAL_ENCOUNTERS)

        print("Seeding clinical procedures...")
        insert_rows(cur, "clinical_procedures", CLINICAL_PROCEDURES)

        print("Seeding coded encounters...")
        insert_rows(cur, "coded_encounters", CODED_ENCOUNTERS)

        print("Seeding coded procedures...")
        insert_rows(cur, "coded_procedures", CODED_PROCEDURES)

        print("Seeding claims...")
        insert_rows(cur, "claims", CLAIMS)

        print("Seeding claim procedures...")
        insert_rows(cur, "claim_procedures", CLAIM_PROCEDURES)

        print("Seeding claim narratives...")
        insert_rows(cur, "claim_narratives", CLAIM_NARRATIVES)

        print("Seeding submission records...")
        insert_rows(cur, "submission_records", SUBMISSION_RECORDS)

        print("Seeding denial records...")
        insert_rows(cur, "denial_records", DENIAL_RECORDS)

        conn.commit()
        print("\nDemo data seeded successfully!")
        print(f"  Tenant:              {TENANT_ID}")
        print(f"  Patients:            {len(PATIENTS)}")
        print(f"  Insurance plans:     {len(INSURANCE_PLANS)}")
        print(f"  Clinical encounters: {len(CLINICAL_ENCOUNTERS)}")
        print(f"  Clinical procedures: {len(CLINICAL_PROCEDURES)}")
        print(f"  Coded encounters:    {len(CODED_ENCOUNTERS)}")
        print(f"  Coded procedures:    {len(CODED_PROCEDURES)}")
        print(f"  Claims:              {len(CLAIMS)}")
        print(f"  Claim procedures:    {len(CLAIM_PROCEDURES)}")
        print(f"  Claim narratives:    {len(CLAIM_NARRATIVES)}")
        print(f"  Submission records:  {len(SUBMISSION_RECORDS)}")
        print(f"  Denial records:      {len(DENIAL_RECORDS)}")

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
