# Buckteeth: AI-Powered Dental Insurance Coding Agent

**Date:** 2026-03-12
**Status:** Draft

## Overview

Buckteeth is an AI-powered dental insurance coding and revenue cycle management platform. It takes clinical input in any form (structured data, free text, voice dictation, images/x-rays), maps procedures to correct insurance codes, builds and submits claims, predicts and manages denials, and tracks the full revenue cycle from coding through payment posting.

The system serves two primary user roles: dentists/hygienists (clinical documentation and code approval) and front desk/insurance coordinators (claim management and billing). It integrates with multiple practice management systems via an adapter layer, supports configurable autonomy from AI suggestions to auto-submission, and is powered by Claude (Anthropic).

## Architecture

### Approach: Modular Monolith with Clear Boundaries

A single deployable application internally organized into well-isolated modules with defined interfaces. Each module has its own domain boundary and communicates through internal interfaces that can later be extracted into independent services when scale demands it.

### Tech Stack

- **Backend:** Python (FastAPI)
- **Frontend:** React (TypeScript)
- **Database:** PostgreSQL (encrypted)
- **File Storage:** S3-compatible (encrypted)
- **AI:** Claude API (Anthropic)
- **Deployment:** Docker containers on AWS (ECS)
- **CI/CD:** GitHub Actions

## Module 1: Ingestion

Accepts clinical input in all forms and normalizes it into a standard internal format (`ClinicalEncounter`).

### Sub-components

- **Text parser** — Extracts procedures, tooth numbers, surfaces, and conditions from free-text notes using Claude. Handles dental shorthand and abbreviations (e.g., "MOD comp #14" -> mesial-occlusal-distal composite restoration, tooth 14).
- **Voice pipeline** — Transcribes dictation (via Whisper or similar), then feeds into the text parser.
- **Image analyzer** — Processes radiographs and intraoral photos via Claude's vision capabilities. Extracts findings (caries, bone loss, fractures) as structured data.
- **Structured data mapper** — Accepts already-structured input (e.g., from PMS imports) and maps to the internal model.

### Output

A `ClinicalEncounter` object — a normalized, structured representation of what happened clinically.

## Module 2: Coding Engine

Takes a `ClinicalEncounter` and produces insurance codes.

### Capabilities

- **CDT code selection** — Maps procedures to correct CDT codes with proper modifiers, surfaces, tooth numbers, and quadrants. Uses retrieval-augmented generation: a local CDT code reference database is searched for candidate codes, Claude receives the clinical context + candidates and selects the best match.
- **ICD-10 cross-coding** — When procedures qualify for medical insurance (e.g., TMJ, sleep apnea appliances, trauma), maps to appropriate diagnosis codes.
- **Bundling/unbundling logic** — Knows which codes can be billed together and which get bundled by payers.
- **Frequency/limitation checking** — Validates against common payer rules (e.g., prophylaxis 2x/year, BWX 1x/year, crowns every 5 years).
- **Code confidence scoring** — Rates confidence in each code selection (0-100), flagging uncertain cases for human review.

### AI Approach

- RAG over memorization — CDT codes, payer rules, and fee schedules are stored in a searchable database, not baked into prompts.
- Structured output — All Claude responses use JSON schemas for parseable, consistent results.
- Confidence-gated autonomy — High confidence (>90%) + routine procedure = auto-approve eligible. Lower confidence or complex procedure = human review queue. Thresholds configurable per office.

## Module 3: Claim Builder

Assembles complete claims from coded encounters.

### Capabilities

- **ADA claim form population** — Fills all required fields on the standard dental claim form.
- **Narrative generator** — Writes clinical narratives for procedures that require justification (e.g., crown buildups, scaling and root planing). Tailored per payer when historical patterns indicate specific language works better.
- **Attachment manager** — Associates x-rays, perio charts, photos with the claim.
- **Pre-authorization builder** — Generates pre-determination requests for major procedures.
- **Coordination of benefits** — Handles primary/secondary insurance sequencing.

## Module 4: Submission Gateway

Routes completed claims to their destination.

### Submission Formats

- **HIPAA 837D** — Standard EDI format for dental claims, required by all clearinghouses.
- **NEA FastAttach** — For electronic attachment submission alongside claims.
- **ADA Dental Claim Form** — Printable/downloadable PDF (2024 version).

### Clearinghouse Adapter Interface

```
ClearinghouseAdapter:
  enroll_provider(provider_info) -> enrollment_status
  submit_claim(claim_837d) -> tracking_id
  submit_attachment(claim_id, attachment) -> confirmation
  check_status(tracking_id) -> claim_status
  receive_era(date_range) -> ERA_835[]
  check_eligibility(patient, payer) -> eligibility_response
```

### Priority Clearinghouses

- DentalXChange (largest dental-specific, good API)
- Tesia/NEA (strong in attachments)
- Availity (large multi-payer network)

### Eligibility Verification

Before coding begins, the system can check patient eligibility and benefits:
- Remaining annual maximum
- Deductible status
- Frequency limitations (last prophy date, last BWX date)
- Waiting periods for major procedures

### ERA/EOB Processing

- Ingest HIPAA 835 files from clearinghouses
- Parse payment details, adjustments, and denial reason codes (CARC/RARC)
- Auto-match to submitted claims
- Route denials to Denial Management module
- Post payments to Revenue Cycle Dashboard

## Module 5: Denial Management

Handles the post-submission lifecycle.

### Capabilities

- **Denial ingestion** — Parses ERA/EOB to identify denials and reason codes.
- **Pre-submission risk scoring** — Before a claim goes out, predicts denial probability based on payer patterns, code combinations, and historical data.
- **Appeal generator** — Drafts appeal letters citing clinical evidence, ADA guidelines, and payer contract terms. Structured for maximum overturn probability based on denial reason code.
- **Denial analytics** — Tracks patterns by payer, code, and provider to surface systemic issues.

## Module 6: PMS Adapter Layer

Plugin architecture for practice management system integrations.

### Standard PMS Interface

```
PMSAdapter:
  authenticate(credentials) -> connection
  pull_patients(filters) -> Patient[]
  pull_encounter(patient_id, date) -> ClinicalEncounter
  pull_treatment_history(patient_id) -> TreatmentHistory
  push_coded_claim(claim) -> submission_result
  pull_era(date_range) -> DenialRecord[]
  get_fee_schedule(payer_id) -> FeeSchedule
```

### Integration Tiers

- **Tier 1: Full API integration** — Bidirectional data sync. Open Dental is the first target (well-documented REST API).
- **Tier 2: Limited/unofficial integration** — Dentrix (SQL Server) and Eaglesoft. Requires a lightweight on-premise bridge agent.
- **Tier 3: File-based integration** — Import/export via CSV, HL7, or SNODENT for PMS systems without APIs.
- **Tier 4: Standalone** — No PMS integration. Users enter data directly into Buckteeth's UI.

### On-Premise Bridge Agent (Tier 2)

A lightweight Python service installed at the dental office that:
- Reads from the local PMS database on a schedule or event trigger
- Encrypts and transmits encounter data to the cloud
- Receives coded claims back and writes to the local PMS
- Can be configured to de-identify data before transmission (PHI stays local)

## Module 7: Revenue Cycle Dashboard

The user-facing layer with role-based views.

### Dentist / Hygienist View

- **Quick input panel** — Large text area for free-text notes, microphone button for voice dictation, drag-and-drop for images/x-rays.
- **Real-time coding preview** — As notes are entered, suggested CDT codes appear with confidence indicators (green/yellow/red).
- **Approve/override** — Tap to accept suggested codes, or click to change. Override reasons captured.
- **Patient context sidebar** — Treatment history, insurance info, remaining benefits, frequency limits.
- **Design goal:** Minimal friction. Under 30 seconds to review codes for a routine visit.

### Front Desk / Insurance Coordinator View

- **Claim Queue Dashboard** — Claims organized by status: ready for review, ready to submit, submitted/pending, action needed, completed.
- **Claim Detail View** — Side-by-side: original clinical notes on left, generated codes on right. AI reasoning expandable per code. Edit any field before submission.
- **Denial Worklist** — Denied claims grouped by reason and payer. AI-generated appeal drafts. Attach additional evidence. Track appeal outcomes.
- **Analytics Dashboard** — Collection rate trends, denial rate by payer/code/provider, average days to payment, AI coding accuracy, revenue impact from appeals and denial prevention.

### Shared Features

- **Audit trail** — Every screen shows who did what and when, including AI actions.
- **Notifications** — Configurable alerts for denials, pre-auth responses, approaching deadlines.
- **Search** — Find any patient, claim, or encounter.
- **Settings** — Configure autonomy levels, notification preferences, default payers, fee schedules.

## Data Model

### Core Entities

**Patient**
- Demographics (name, DOB, gender)
- Insurance plans (primary, secondary) with subscriber info, group numbers, payer IDs
- Treatment history (for frequency/limitation checking)

**ClinicalEncounter**
- Patient reference
- Provider (dentist/hygienist)
- Date of service
- List of `ClinicalProcedure` entries:
  - Procedure description (free text or structured)
  - Tooth number(s), surface(s), quadrant
  - Diagnosis/condition
  - Supporting evidence references (x-ray IDs, photo IDs)
- Raw input artifacts (original notes, audio file, images)

**CodedEncounter**
- Links back to `ClinicalEncounter`
- List of `CodedProcedure` entries:
  - CDT code + description
  - ICD-10 code(s) if cross-coded
  - Tooth/surface/quadrant
  - Confidence score (0-100)
  - AI reasoning (why this code was selected)
  - Flags (bundling risk, frequency concern, needs narrative)
- Human review status (pending, approved, modified, rejected)
- Modification history (what the human changed and why)

**Claim**
- Claim ID, status (draft, ready, submitted, accepted, denied, appealed, paid)
- Coded procedures
- Generated narrative(s)
- Attachment references
- Pre-authorization status
- Primary/secondary payer routing
- Fee schedule amounts (submitted vs. allowed vs. paid)

**SubmissionRecord**
- Claim reference
- Submission channel (clearinghouse, PMS, paper)
- Timestamp, tracking/confirmation number
- Response/acknowledgment

**DenialRecord**
- Claim reference
- Denial reason code (CARC/RARC)
- Denied amount
- AI risk score (pre-submission prediction)
- Appeal status, appeal document reference

**AppealDocument**
- Denial reference
- Generated letter text
- Supporting evidence citations
- Outcome (overturned, upheld, partial)

**AuditLog**
- Every AI decision: input, output, reasoning
- Every human override: original value, new value, reason
- Timestamps and user IDs throughout

### Design Principles

- **Immutable inputs** — Raw clinical notes, audio, and images are never modified, only interpreted.
- **Full traceability** — Every code suggestion links back to clinical evidence and AI reasoning.
- **Human override tracking** — When a human changes an AI suggestion, both the original and the change are captured, creating a feedback loop for improving accuracy.

## AI Pipeline & Claude Integration

### Prompt Chains

1. **Clinical Note Interpretation** — Free-text/dictation -> structured procedure data. Few-shot examples of common dental note formats. Handles shorthand and abbreviations.

2. **CDT Code Selection** — Structured procedure -> CDT code(s). RAG approach: search local CDT database for candidates, Claude reasons over candidates + clinical context.

3. **Medical Cross-Coding** — Flagged procedures -> ICD-10 codes. Triggered for TMJ, sleep apnea, trauma, pathology, biopsies.

4. **Narrative Generation** — Coded procedure + clinical evidence -> payer-facing justification narrative. Tailored per payer based on historical success patterns.

5. **Denial Risk Prediction** — Completed claim -> risk score + specific concerns + suggested modifications. Analyzes against payer rules, historical patterns, coding pitfalls.

6. **Appeal Letter Generation** — Denied claim + reason + clinical docs -> formal appeal letter. Cites clinical evidence, ADA guidelines, CDT descriptors, payer contract terms.

### AI Architecture Decisions

- **RAG over memorization** — Codes, rules, and fee schedules stored in searchable database, not in prompts.
- **Structured output** — All Claude responses use JSON schemas.
- **Confidence-gated autonomy** — Configurable thresholds per office. High confidence + routine = auto-approve eligible.
- **Prompt versioning** — All prompts versioned and stored in database for tracking and rollback.
- **Feedback loop** — Human overrides collected and used to refine prompts and retrieval relevance.

## CDT Code Reference & Knowledge Base

### CDT Code Database

Full CDT code set (~800 codes across 12 categories). Each code stored with:
- Code number and official ADA descriptor
- Category and subcategory
- Common clinical scenarios
- Commonly confused codes
- Bundling rules
- Typical frequency limitations by payer type
- Whether narrative is typically required
- Common denial reasons

**Licensing:** CDT codes are copyrighted by the ADA. The system requires an ADA license for official descriptors. Built to load codes from a configurable data source.

### Payer Intelligence Database

Per-insurance-company rules and patterns:
- Frequency limitations
- Age limitations
- Downcoding patterns
- Pre-authorization requirements
- Preferred narrative language
- Known bundling behavior

Initial manual curation for major payers: Delta Dental, MetLife, Cigna, Aetna, United Healthcare Dental, Guardian. Enriched over time from anonymized, aggregated denial/approval patterns across tenants.

### Fee Schedule Management

- UCR (Usual, Customary, and Reasonable) fee schedules
- Per-payer contracted rates where available

### Knowledge Base Updates

- CDT codes update annually (effective January 1)
- Payer rules change frequently
- Admin interface for uploading new code sets
- Payer rules versioned with changelog

## Security & Compliance

### HIPAA Compliance

**Data protection:**
- All PHI encrypted at rest (AES-256) and in transit (TLS 1.3)
- Database-level encryption with per-tenant keys
- S3 server-side encryption for files
- BAA required with Anthropic (Claude API), AWS, and clearinghouse partners

**Access controls:**
- Role-based access control (RBAC): dentist, hygienist, front desk, office admin
- Multi-factor authentication required
- Session timeout after configurable inactivity
- Row-level security — users only see patients from their practice

**Audit & logging:**
- All PHI access logged with user, timestamp, and action
- All AI interactions logged (input, output, reasoning)
- Logs retained minimum 6 years per HIPAA requirements
- Tamper-evident audit logs (append-only, hashed chain)

### Deployment Architecture (Hybrid Cloud)

**Cloud tier (AWS):**
- FastAPI application servers behind load balancer
- PostgreSQL (RDS) with encryption
- S3 for document/image storage
- Claude API for AI processing
- Clearinghouse API integrations

**On-premise bridge (optional):**
- Lightweight Python agent at dental office
- Encrypted tunnel to cloud
- Configurable PHI de-identification in transit

**Multi-tenancy:**
- Each dental office is an isolated tenant
- Schema-per-tenant or row-level isolation at database level
- Tenant-specific configuration for autonomy, payers, fee schedules

### Infrastructure

- **CI/CD:** GitHub Actions
- **Containers:** Docker, deployed via AWS ECS
- **Monitoring:** Application metrics, error tracking, uptime monitoring
- **Backups:** Automated daily with point-in-time recovery, 30-day retention
