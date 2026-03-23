#!/usr/bin/env python3
"""
Phenomenal Problems — Demo Seed Script v2
==========================================
Creates realistic demo data for the Buckteeth dental billing platform.
Idempotent: uses deterministic UUIDs (uuid5) and clears tenant data first.
"""

import json
import uuid
import psycopg2
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_DSN = "postgresql://buckteeth:m2CttrcKtbssGVMBfWl3NKxpWwpWAKPc@localhost:5432/buckteeth"
TENANT = uuid.UUID("00000000-0000-0000-0000-000000000001")
NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")  # namespace for uuid5


def uid(name: str) -> str:
    """Deterministic UUID from a human-readable name."""
    return str(uuid.uuid5(NS, name))


# ---------------------------------------------------------------------------
# Delete order (reverse FK)
# ---------------------------------------------------------------------------
DELETE_ORDER = [
    "appeal_documents",
    "commissioner_letters",
    "era_records",
    "submission_records",
    "denial_records",
    "claim_narratives",
    "claim_attachments",
    "claim_procedures",
    "claims",
    "coded_procedures",
    "coded_encounters",
    "clinical_procedures",
    "clinical_encounters",
    "insurance_plans",
    "patients",
]

# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------
PATIENTS = [
    ("maria_gonzalez",   "Maria",   "Gonzalez", "1985-03-14", "female"),
    ("james_thompson",   "James",   "Thompson", "1972-11-28", "male"),
    ("aisha_patel",      "Aisha",   "Patel",    "1990-07-02", "female"),
    ("robert_chen",      "Robert",  "Chen",     "1968-01-19", "male"),
    ("linda_williams",   "Linda",   "Williams", "1955-09-07", "female"),
    ("derek_johnson",    "Derek",   "Johnson",  "1998-12-30", "male"),
    ("susan_park",       "Susan",   "Park",     "1982-08-20", "female"),
    ("michael_rivera",   "Michael", "Rivera",   "1975-04-11", "male"),
]

# ---------------------------------------------------------------------------
# Insurance Plans  (key, patient_key, payer_name, payer_id, sub_id, group, plan_type)
# ---------------------------------------------------------------------------
INSURANCE = [
    ("ins_maria",        "maria_gonzalez",  "Delta Dental Premier",       "DDCA1", "DD-889-2041573", "GRP-44821", "primary"),
    ("ins_james",        "james_thompson",  "MetLife Dental",             "61109", "ML-332-7891234", "GRP-55012", "primary"),
    ("ins_aisha",        "aisha_patel",     "Cigna Dental PPO",           "62308", "CG-445-9012345", "GRP-33198", "primary"),
    ("ins_robert_pri",   "robert_chen",     "Aetna Dental PPO",           "60054", "AE-221-3456789", "GRP-77543", "primary"),
    ("ins_robert_sec",   "robert_chen",     "Guardian Dental",            "63959", "GD-221-3456789", "GRP-88120", "secondary"),
    ("ins_linda",        "linda_williams",  "UnitedHealthcare Dental",    "87726", "UH-667-1234567", "GRP-22876", "primary"),
    ("ins_derek",        "derek_johnson",   "Delta Dental of California", "DDCA1", "DD-998-7654321", "GRP-11345", "primary"),
    ("ins_susan",        "susan_park",      "Anthem BCBS Dental",         "47198", "AN-554-2345678", "GRP-66789", "primary"),
    ("ins_michael",      "michael_rivera",  "Humana Dental",              "61101", "HU-443-8901234", "GRP-99234", "primary"),
]

# ---------------------------------------------------------------------------
# Clinical Encounters
# ---------------------------------------------------------------------------
ENCOUNTERS = [
    {
        "key": "enc_maria",
        "patient": "maria_gonzalez",
        "provider": "Dr. Sarah Mitchell, DDS",
        "dos": "2026-03-10",
        "notes": "Routine recall. Prophylaxis and 4 bitewing radiographs performed. Light calculus removal. Oral hygiene instruction given. No carious lesions.",
        "input_type": "typed",
        "status": "coded",
    },
    {
        "key": "enc_james",
        "patient": "james_thompson",
        "provider": "Dr. David Park, DDS",
        "dos": "2026-03-12",
        "notes": "Crown preparation tooth #30. Large failing MOD amalgam with recurrent decay at mesial and distal margins. Approximately 65% of tooth structure compromised. Core buildup performed. Full coverage PFM crown preparation completed.",
        "input_type": "typed",
        "status": "coded",
    },
    {
        "key": "enc_aisha",
        "patient": "aisha_patel",
        "provider": "Dr. Sarah Mitchell, DDS",
        "dos": "2026-03-14",
        "notes": "Scaling and root planing upper right quadrant. Patient presents with Stage II periodontitis. Probing depths 5-7mm with bleeding on probing in UR quadrant. Radiographic evidence of moderate horizontal bone loss.",
        "input_type": "typed",
        "status": "coded",
    },
    {
        "key": "enc_robert",
        "patient": "robert_chen",
        "provider": "Dr. David Park, DDS",
        "dos": "2026-03-17",
        "notes": "Root canal therapy tooth #14. Patient presented with irreversible pulpitis. Positive response to cold testing that lingered > 30 seconds. Periapical radiograph shows widened PDL space. Access, instrumentation and obturation completed.",
        "input_type": "typed",
        "status": "coded",
    },
    {
        "key": "enc_linda",
        "patient": "linda_williams",
        "provider": "Dr. Rachel Torres, DDS, OMS",
        "dos": "2026-03-19",
        "notes": "Surgical extraction of tooth #17. Non-restorable due to extensive decay below CEJ with grade II furcation involvement. Flap raised, buccal bone removed, tooth sectioned and removed. Socket grafted with bone allograft. Sutures placed.",
        "input_type": "typed",
        "status": "coded",
    },
    {
        "key": "enc_derek",
        "patient": "derek_johnson",
        "provider": "Dr. Sarah Mitchell, DDS",
        "dos": "2026-03-21",
        "notes": "Comprehensive oral evaluation new patient. Full mouth series of radiographs taken. Caries detected on #19 DO and #3 MO. Treatment plan discussed.",
        "input_type": "typed",
        "status": "coded",
    },
]

# ---------------------------------------------------------------------------
# Clinical Procedures  (key, encounter_key, description, tooth_numbers, surfaces, quadrant, diagnosis)
# ---------------------------------------------------------------------------
CLIN_PROCS = [
    ("cp_maria_prophy", "enc_maria", "Adult prophylaxis — light calculus removal", [None], None, None, None),
    ("cp_maria_bwx",    "enc_maria", "4 bitewing radiographs", [None], None, None, None),
    ("cp_james_core",   "enc_james", "Core buildup tooth #30", [30], ["M","O","D"], None, "Recurrent caries with large failing MOD amalgam"),
    ("cp_james_crown",  "enc_james", "PFM crown preparation tooth #30", [30], None, None, "Approximately 65% of tooth structure compromised"),
    ("cp_aisha_srp",    "enc_aisha", "Scaling and root planing upper right quadrant", None, None, "UR", "Stage II periodontitis, probing depths 5-7mm"),
    ("cp_robert_rct",   "enc_robert", "Root canal therapy tooth #14", [14], None, None, "Irreversible pulpitis with widened PDL space"),
    ("cp_linda_surg",   "enc_linda", "Surgical extraction tooth #17", [17], None, None, "Non-restorable, decay below CEJ, grade II furcation"),
    ("cp_linda_graft",  "enc_linda", "Bone allograft socket graft tooth #17", [17], None, None, "Socket preservation post-extraction"),
    ("cp_derek_eval",   "enc_derek", "Comprehensive oral evaluation — new patient", [None], None, None, None),
    ("cp_derek_fmx",    "enc_derek", "Full mouth series of radiographs", [None], None, None, None),
]

# ---------------------------------------------------------------------------
# Coded Encounters (first 4 encounters)
# ---------------------------------------------------------------------------
CODED_ENCOUNTERS = [
    ("ce_maria",  "enc_maria",  "approved"),
    ("ce_james",  "enc_james",  "approved"),
    ("ce_aisha",  "enc_aisha",  "approved"),
    ("ce_robert", "enc_robert", "approved"),
]

# ---------------------------------------------------------------------------
# Coded Procedures
# (key, coded_enc_key, clin_proc_key, cdt_code, cdt_desc, tooth, surfaces, quadrant, confidence, reasoning, icd10s, flags)
# ---------------------------------------------------------------------------
CODED_PROCS = [
    ("cdp_maria_prophy", "ce_maria", "cp_maria_prophy", "D1110",
     "Prophylaxis — adult", None, None, None, 97,
     "Adult patient presenting for routine recall with light calculus. D1110 is appropriate for prophylaxis on patients with permanent dentition.",
     ["Z01.20"], None),
    ("cdp_maria_bwx", "ce_maria", "cp_maria_bwx", "D0274",
     "Bitewings — four radiographic images", None, None, None, 96,
     "Four bitewing radiographs taken during recall visit. D0274 covers 4 BW images.",
     ["Z01.20"], None),
    ("cdp_james_core", "ce_james", "cp_james_core", "D2950",
     "Core buildup, including any pins when required", "30", "MOD", None, 91,
     "Core buildup performed on tooth #30 prior to crown due to extensive loss of tooth structure from failing amalgam and recurrent caries.",
     ["K02.9", "K08.59"], None),
    ("cdp_james_crown", "ce_james", "cp_james_crown", "D2750",
     "Crown — porcelain fused to high noble metal", "30", None, None, 89,
     "Full coverage PFM crown is indicated given 65% of tooth structure compromised. High noble metal chosen for posterior tooth requiring maximum strength.",
     ["K02.9", "K08.59"], json.dumps(["Verify material choice with lab prescription"])),
    ("cdp_aisha_srp", "ce_aisha", "cp_aisha_srp", "D4341",
     "Periodontal scaling and root planing — four or more teeth per quadrant", None, None, "UR", 93,
     "Patient has Stage II periodontitis with 5-7mm probing depths and bleeding on probing in upper right quadrant. SRP is standard of care. D4341 used as ≥4 teeth affected.",
     ["K05.319"], None),
    ("cdp_robert_rct", "ce_robert", "cp_robert_rct", "D3320",
     "Endodontic therapy, premolar tooth (excluding final restoration)", "14", None, None, 95,
     "Tooth #14 is a premolar. Irreversible pulpitis confirmed by prolonged cold response (>30s). Widened PDL on radiograph supports diagnosis. D3320 is correct for premolar endodontic therapy.",
     ["K04.01", "K04.6"], None),
]

# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------
CLAIMS = [
    {
        "key": "clm_maria",
        "coded_enc": "ce_maria",
        "patient": "maria_gonzalez",
        "provider": "Dr. Sarah Mitchell, DDS",
        "dos": "2026-03-10",
        "status": "accepted",
        "pri_payer": "Delta Dental Premier",  "pri_payer_id": "DDCA1",
        "pri_sub": "DD-889-2041573",           "pri_group": "GRP-44821",
        "sec_payer": None, "sec_payer_id": None, "sec_sub": None, "sec_group": None,
        "preauth_required": False,
        "total_submitted": 235.0, "total_allowed": 210.0, "total_paid": 185.0,
    },
    {
        "key": "clm_james",
        "coded_enc": "ce_james",
        "patient": "james_thompson",
        "provider": "Dr. David Park, DDS",
        "dos": "2026-03-12",
        "status": "submitted",
        "pri_payer": "MetLife Dental",  "pri_payer_id": "61109",
        "pri_sub": "ML-332-7891234",   "pri_group": "GRP-55012",
        "sec_payer": None, "sec_payer_id": None, "sec_sub": None, "sec_group": None,
        "preauth_required": True, "preauth_number": "PA-2026-44821", "preauth_status": "approved",
        "total_submitted": 1550.0, "total_allowed": None, "total_paid": None,
    },
    {
        "key": "clm_aisha",
        "coded_enc": "ce_aisha",
        "patient": "aisha_patel",
        "provider": "Dr. Sarah Mitchell, DDS",
        "dos": "2026-03-14",
        "status": "denied",
        "pri_payer": "Cigna Dental PPO", "pri_payer_id": "62308",
        "pri_sub": "CG-445-9012345",    "pri_group": "GRP-33198",
        "sec_payer": None, "sec_payer_id": None, "sec_sub": None, "sec_group": None,
        "preauth_required": False,
        "total_submitted": 275.0, "total_allowed": 0.0, "total_paid": 0.0,
    },
    {
        "key": "clm_robert",
        "coded_enc": "ce_robert",
        "patient": "robert_chen",
        "provider": "Dr. David Park, DDS",
        "dos": "2026-03-17",
        "status": "draft",
        "pri_payer": "Aetna Dental PPO", "pri_payer_id": "60054",
        "pri_sub": "AE-221-3456789",    "pri_group": "GRP-77543",
        "sec_payer": "Guardian Dental", "sec_payer_id": "63959",
        "sec_sub": "GD-221-3456789",   "sec_group": "GRP-88120",
        "preauth_required": False,
        "total_submitted": 950.0, "total_allowed": None, "total_paid": None,
    },
    {
        "key": "clm_linda",
        "coded_enc": "ce_maria",  # placeholder — we need a coded encounter; Linda's doesn't exist
        "patient": "linda_williams",
        "provider": "Dr. Rachel Torres, DDS, OMS",
        "dos": "2026-03-19",
        "status": "accepted",
        "pri_payer": "UnitedHealthcare Dental", "pri_payer_id": "87726",
        "pri_sub": "UH-667-1234567",           "pri_group": "GRP-22876",
        "sec_payer": None, "sec_payer_id": None, "sec_sub": None, "sec_group": None,
        "preauth_required": False,
        "total_submitted": 475.0, "total_allowed": 420.0, "total_paid": 380.0,
    },
]

# We need coded encounters for Linda (and Derek) for the FK on claims.
# Let's add them so we can reference them.
CODED_ENCOUNTERS += [
    ("ce_linda", "enc_linda", "approved"),
    ("ce_derek", "enc_derek", "pending_review"),
]

# Also add coded procedures for Linda
CODED_PROCS += [
    ("cdp_linda_surg", "ce_linda", "cp_linda_surg", "D7210",
     "Extraction, erupted tooth requiring removal of bone and/or sectioning of tooth", "17", None, None, 94,
     "Surgical extraction indicated due to extensive subgingival decay below CEJ with grade II furcation involvement. Required flap elevation, bone removal, and tooth sectioning.",
     ["K04.7", "K08.109"], None),
    ("cdp_linda_graft", "ce_linda", "cp_linda_graft", "D7953",
     "Bone replacement graft for ridge preservation — per site", "17", None, None, 88,
     "Socket grafted with bone allograft for ridge preservation following surgical extraction. D7953 appropriate for bone graft per extraction site.",
     ["K08.109"], json.dumps(["Verify graft material documentation"])),
    ("cdp_derek_eval", "ce_derek", "cp_derek_eval", "D0150",
     "Comprehensive oral evaluation — new or established patient", None, None, None, 98,
     "New patient comprehensive evaluation. Clinical and radiographic assessment performed with findings of caries on teeth #19 and #3.",
     ["Z01.20"], None),
    ("cdp_derek_fmx", "ce_derek", "cp_derek_fmx", "D0210",
     "Intraoral — complete series of radiographic images", None, None, None, 97,
     "Full mouth series taken for new patient comprehensive evaluation. D0210 is the standard code for a complete series.",
     ["Z01.20"], None),
]

# Fix Linda's claim to point to her coded encounter
CLAIMS[4]["coded_enc"] = "ce_linda"

# ---------------------------------------------------------------------------
# Claim Procedures  (key, claim_key, coded_proc_key, cdt, desc, tooth, surfaces, quadrant, fee_sub, fee_allowed, fee_paid)
# ---------------------------------------------------------------------------
CLAIM_PROCS = [
    ("clmp_maria_prophy", "clm_maria", "cdp_maria_prophy", "D1110", "Prophylaxis — adult", None, None, None, 150.0, 135.0, 120.0),
    ("clmp_maria_bwx",    "clm_maria", "cdp_maria_bwx",    "D0274", "Bitewings — four radiographic images", None, None, None, 85.0, 75.0, 65.0),
    ("clmp_james_core",   "clm_james", "cdp_james_core",   "D2950", "Core buildup, including any pins when required", "30", "MOD", None, 350.0, None, None),
    ("clmp_james_crown",  "clm_james", "cdp_james_crown",  "D2750", "Crown — porcelain fused to high noble metal", "30", None, None, 1200.0, None, None),
    ("clmp_aisha_srp",    "clm_aisha", "cdp_aisha_srp",    "D4341", "Periodontal scaling and root planing — four or more teeth per quadrant", None, None, "UR", 275.0, 0.0, 0.0),
    ("clmp_robert_rct",   "clm_robert","cdp_robert_rct",   "D3320", "Endodontic therapy, premolar tooth", "14", None, None, 950.0, None, None),
    ("clmp_linda_surg",   "clm_linda", "cdp_linda_surg",   "D7210", "Extraction, erupted tooth requiring removal of bone and/or sectioning", "17", None, None, 350.0, 310.0, 280.0),
    ("clmp_linda_graft",  "clm_linda", "cdp_linda_graft",  "D7953", "Bone replacement graft for ridge preservation — per site", "17", None, None, 125.0, 110.0, 100.0),
]

# ---------------------------------------------------------------------------
# Claim Narratives
# ---------------------------------------------------------------------------
NARRATIVES = [
    ("narr_james", "clm_james", "D2750",
     "Large failing MOD amalgam restoration on tooth #30 with recurrent caries at mesial and distal margins. Approximately 65% of clinical crown compromised. Direct restoration inadequate due to insufficient remaining tooth structure for retention. Full coverage crown necessary to restore function and prevent fracture.",
     "ai", True),
    ("narr_aisha", "clm_aisha", "D4341",
     "Patient presents with Stage II, Grade B periodontitis in the upper right quadrant. Probing depths of 5-7mm with bleeding on probing at teeth #2-5. Bitewing radiographs demonstrate moderate horizontal bone loss of 20-30% around affected teeth. Scaling and root planing is medically necessary to arrest disease progression.",
     "ai", True),
]

# ---------------------------------------------------------------------------
# Submission Records
# ---------------------------------------------------------------------------
SUBMISSIONS = [
    ("sub_maria", "clm_maria", "clearinghouse", "DentalXChange", "TRK-AA1234", "CNF-001122", "accepted", None),
    ("sub_linda", "clm_linda", "clearinghouse", "DentalXChange", "TRK-BB5678", "CNF-003344", "accepted", None),
]

# ---------------------------------------------------------------------------
# Denial Records
# ---------------------------------------------------------------------------
DENIALS = [
    ("den_aisha", "clm_aisha", "N362",
     "Periodontal charting not submitted with claim. Per plan requirements, scaling and root planing claims (D4341/D4342) must include full periodontal charting with probing depths, bleeding on probing, and clinical attachment levels.",
     275.0, "Cigna Dental PPO", "denied"),
    ("den_james", "clm_james", "197",
     "Pre-authorization was not obtained prior to service. Crown procedures require predetermination.",
     1200.0, "MetLife Dental", "appealed"),
]


# ===========================================================================
# Main
# ===========================================================================
def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    tenant = str(TENANT)

    # ---- 1. Clear existing data ----
    print("Clearing existing data for tenant …")
    for table in DELETE_ORDER:
        cur.execute(f"DELETE FROM {table} WHERE tenant_id = %s", (tenant,))
        print(f"  {table}: {cur.rowcount} rows deleted")

    # ---- 2. Patients ----
    print("\nInserting patients …")
    for key, first, last, dob, gender in PATIENTS:
        cur.execute(
            "INSERT INTO patients (id, tenant_id, first_name, last_name, date_of_birth, gender) VALUES (%s,%s,%s,%s,%s,%s)",
            (uid(key), tenant, first, last, dob, gender),
        )
    print(f"  {len(PATIENTS)} patients")

    # ---- 3. Insurance Plans ----
    print("Inserting insurance plans …")
    for key, pat_key, payer_name, payer_id, sub_id, group, plan_type in INSURANCE:
        cur.execute(
            "INSERT INTO insurance_plans (id, tenant_id, patient_id, payer_name, payer_id, subscriber_id, group_number, plan_type) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(key), tenant, uid(pat_key), payer_name, payer_id, sub_id, group, plan_type),
        )
    print(f"  {len(INSURANCE)} plans")

    # ---- 4. Clinical Encounters ----
    print("Inserting clinical encounters …")
    for enc in ENCOUNTERS:
        cur.execute(
            "INSERT INTO clinical_encounters (id, tenant_id, patient_id, provider_name, date_of_service, raw_notes, raw_input_type, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(enc["key"]), tenant, uid(enc["patient"]), enc["provider"], enc["dos"], enc["notes"], enc["input_type"], enc["status"]),
        )
    print(f"  {len(ENCOUNTERS)} encounters")

    # ---- 5. Clinical Procedures ----
    print("Inserting clinical procedures …")
    for key, enc_key, desc, teeth, surfaces, quad, diag in CLIN_PROCS:
        cur.execute(
            "INSERT INTO clinical_procedures (id, tenant_id, encounter_id, description, tooth_numbers, surfaces, quadrant, diagnosis) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(key), tenant, uid(enc_key), desc,
             json.dumps(teeth) if teeth else None,
             json.dumps(surfaces) if surfaces else None,
             quad, diag),
        )
    print(f"  {len(CLIN_PROCS)} procedures")

    # ---- 6. Coded Encounters ----
    print("Inserting coded encounters …")
    for key, enc_key, review in CODED_ENCOUNTERS:
        cur.execute(
            "INSERT INTO coded_encounters (id, tenant_id, encounter_id, review_status) VALUES (%s,%s,%s,%s)",
            (uid(key), tenant, uid(enc_key), review),
        )
    print(f"  {len(CODED_ENCOUNTERS)} coded encounters")

    # ---- 7. Coded Procedures ----
    print("Inserting coded procedures …")
    for (key, ce_key, cp_key, cdt, cdt_desc, tooth, surfaces, quad,
         confidence, reasoning, icd10s, flags) in CODED_PROCS:
        cur.execute(
            """INSERT INTO coded_procedures
               (id, tenant_id, coded_encounter_id, clinical_procedure_id,
                cdt_code, cdt_description, tooth_number, surfaces, quadrant,
                confidence_score, ai_reasoning, icd10_codes, flags)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid(key), tenant, uid(ce_key), uid(cp_key),
             cdt, cdt_desc, tooth, surfaces, quad,
             confidence, reasoning,
             json.dumps(icd10s) if icd10s else None,
             flags),
        )
    print(f"  {len(CODED_PROCS)} coded procedures")

    # ---- 8. Claims ----
    print("Inserting claims …")
    for clm in CLAIMS:
        cur.execute(
            """INSERT INTO claims
               (id, tenant_id, coded_encounter_id, patient_id, provider_name,
                date_of_service, status, primary_payer_name, primary_payer_id,
                primary_subscriber_id, primary_group_number,
                secondary_payer_name, secondary_payer_id,
                secondary_subscriber_id, secondary_group_number,
                preauth_required, preauth_number, preauth_status,
                total_fee_submitted, total_fee_allowed, total_fee_paid)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid(clm["key"]), tenant, uid(clm["coded_enc"]), uid(clm["patient"]),
             clm["provider"], clm["dos"], clm["status"],
             clm["pri_payer"], clm["pri_payer_id"], clm["pri_sub"], clm["pri_group"],
             clm.get("sec_payer"), clm.get("sec_payer_id"),
             clm.get("sec_sub"), clm.get("sec_group"),
             clm["preauth_required"],
             clm.get("preauth_number"), clm.get("preauth_status"),
             clm["total_submitted"], clm.get("total_allowed"), clm.get("total_paid")),
        )
    print(f"  {len(CLAIMS)} claims")

    # ---- 9. Claim Procedures ----
    print("Inserting claim procedures …")
    for key, clm_key, cp_key, cdt, desc, tooth, surfaces, quad, fee_sub, fee_allow, fee_paid in CLAIM_PROCS:
        cur.execute(
            """INSERT INTO claim_procedures
               (id, tenant_id, claim_id, coded_procedure_id,
                cdt_code, cdt_description, tooth_number, surfaces, quadrant,
                fee_submitted, fee_allowed, fee_paid)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid(key), tenant, uid(clm_key), uid(cp_key),
             cdt, desc, tooth, surfaces, quad, fee_sub, fee_allow, fee_paid),
        )
    print(f"  {len(CLAIM_PROCS)} claim procedures")

    # ---- 10. Claim Narratives ----
    print("Inserting claim narratives …")
    for key, clm_key, cdt, text, gen_by, payer_tailored in NARRATIVES:
        cur.execute(
            """INSERT INTO claim_narratives
               (id, tenant_id, claim_id, cdt_code, narrative_text, generated_by, payer_tailored)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (uid(key), tenant, uid(clm_key), cdt, text, gen_by, payer_tailored),
        )
    print(f"  {len(NARRATIVES)} narratives")

    # ---- 11. Submission Records ----
    print("Inserting submission records …")
    for key, clm_key, channel, ch_name, tracking, confirm, status, err in SUBMISSIONS:
        cur.execute(
            """INSERT INTO submission_records
               (id, tenant_id, claim_id, channel, clearinghouse_name,
                tracking_number, confirmation_number, status, error_message, idempotency_key)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid(key), tenant, uid(clm_key), channel, ch_name,
             tracking, confirm, status, err, uid(key + "_idem")),
        )
    print(f"  {len(SUBMISSIONS)} submission records")

    # ---- 12. Denial Records ----
    print("Inserting denial records …")
    for key, clm_key, code, desc, amount, payer, status in DENIALS:
        cur.execute(
            """INSERT INTO denial_records
               (id, tenant_id, claim_id, denial_reason_code, denial_reason_description,
                denied_amount, payer_name, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid(key), tenant, uid(clm_key), code, desc, amount, payer, status),
        )
    print(f"  {len(DENIALS)} denial records")

    # ---- Commit ----
    conn.commit()
    print("\n=== Demo seed complete. All data committed. ===")

    # ---- Verification ----
    print("\nVerification counts:")
    for table in ["patients", "insurance_plans", "clinical_encounters", "clinical_procedures",
                  "coded_encounters", "coded_procedures", "claims", "claim_procedures",
                  "claim_narratives", "submission_records", "denial_records"]:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = %s", (tenant,))
        count = cur.fetchone()[0]
        print(f"  {table}: {count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
