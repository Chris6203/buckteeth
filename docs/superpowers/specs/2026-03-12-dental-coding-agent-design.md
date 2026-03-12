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
- **Auth:** AWS Cognito (OAuth2/OIDC) with SAML support for enterprise offices
- **Voice Transcription:** AWS Transcribe Medical (HIPAA-eligible, no additional BAA complexity)
- **Deployment:** Docker containers on AWS (ECS)
- **CI/CD:** GitHub Actions
- **Migrations:** Alembic for database schema versioning

## Module 1: Ingestion

Accepts clinical input in all forms and normalizes it into a standard internal format (`ClinicalEncounter`).

### Sub-components

- **Text parser** — Extracts procedures, tooth numbers, surfaces, and conditions from free-text notes using Claude. Handles dental shorthand and abbreviations (e.g., "MOD comp #14" -> mesial-occlusal-distal composite restoration, tooth 14).
- **Voice pipeline** — Transcribes dictation via AWS Transcribe Medical (HIPAA-eligible, supports dental vocabulary, no additional BAA beyond AWS). Transcribed text feeds into the text parser.
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
- **Debounced coding preview** — After a 2-second pause in typing (or on explicit "Code This" action), suggested CDT codes appear with confidence indicators (green/yellow/red). Uses streaming responses from Claude to show results progressively.
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

## API Contract

The React frontend communicates with the FastAPI backend via a REST API. All endpoints require authentication via JWT (issued by AWS Cognito). Responses use standard HTTP status codes with structured error bodies.

### Authentication Flow

1. User logs in via Cognito hosted UI (supports MFA, SAML for enterprise)
2. Cognito issues JWT access token + refresh token
3. Frontend includes `Authorization: Bearer <token>` on all API calls
4. Backend validates JWT signature and extracts tenant_id + role from claims
5. Row-level security enforced: all queries scoped to the authenticated tenant

### Core API Endpoints

```
# Authentication
POST   /auth/login                          -> JWT tokens
POST   /auth/refresh                        -> refreshed JWT
POST   /auth/logout                         -> revoke session

# Patients
GET    /patients                            -> Patient[] (paginated)
GET    /patients/{id}                       -> Patient
POST   /patients                            -> Patient (create)
PUT    /patients/{id}                       -> Patient (update)
GET    /patients/{id}/treatment-history     -> TreatmentHistory
GET    /patients/{id}/eligibility           -> EligibilityResponse

# Clinical Encounters
POST   /encounters                          -> ClinicalEncounter (create from structured input)
POST   /encounters/from-notes               -> ClinicalEncounter (create from free text, triggers AI parsing)
POST   /encounters/from-voice               -> ClinicalEncounter (upload audio, triggers transcription + parsing)
POST   /encounters/from-images              -> ClinicalEncounter (upload images, triggers AI analysis)
GET    /encounters/{id}                     -> ClinicalEncounter

# Coding
POST   /encounters/{id}/code               -> CodedEncounter (triggers AI coding)
GET    /encounters/{id}/coded               -> CodedEncounter
PUT    /encounters/{id}/coded/procedures/{pid} -> CodedProcedure (human override)
POST   /encounters/{id}/coded/approve       -> CodedEncounter (approve all codes)

# Coding preview (debounced from frontend)
POST   /coding/preview                      -> CodedProcedure[] (streaming SSE response)

# Claims
POST   /claims                              -> Claim (build from coded encounter)
GET    /claims                              -> Claim[] (paginated, filterable by status)
GET    /claims/{id}                         -> Claim (full detail)
PUT    /claims/{id}                         -> Claim (edit before submission)
POST   /claims/{id}/submit                  -> SubmissionRecord
POST   /claims/batch-submit                 -> SubmissionRecord[] (submit multiple)
GET    /claims/{id}/risk-score              -> DenialRiskAssessment

# Denials & Appeals
GET    /denials                             -> DenialRecord[] (paginated)
GET    /denials/{id}                        -> DenialRecord
POST   /denials/{id}/generate-appeal        -> AppealDocument (AI-drafted)
PUT    /denials/{id}/appeal                 -> AppealDocument (edit appeal)
POST   /denials/{id}/submit-appeal          -> SubmissionRecord

# Analytics
GET    /analytics/collection-rates          -> CollectionRateData
GET    /analytics/denial-rates              -> DenialRateData
GET    /analytics/coding-accuracy           -> CodingAccuracyData
GET    /analytics/revenue-impact            -> RevenueImpactData

# Admin / Settings
GET    /settings                            -> TenantSettings
PUT    /settings                            -> TenantSettings
GET    /settings/autonomy                   -> AutonomyConfig
PUT    /settings/autonomy                   -> AutonomyConfig
POST   /admin/pms/connect                   -> PMSConnectionStatus
GET    /admin/audit-log                     -> AuditLogEntry[] (paginated)
```

### Error Response Format

```json
{
  "error": {
    "code": "CLAIM_VALIDATION_FAILED",
    "message": "Missing required field: subscriber_id",
    "details": [
      {"field": "subscriber_id", "reason": "required"}
    ]
  }
}
```

### Streaming (SSE)

The `/coding/preview` endpoint uses Server-Sent Events to stream coding suggestions progressively as Claude processes the input. The frontend opens an SSE connection and receives incremental `CodedProcedure` objects. Since the browser `EventSource` API cannot send custom headers, SSE authentication uses a short-lived token passed as a query parameter (generated via a dedicated `/auth/sse-token` endpoint, 60-second TTL, single-use).

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

### PHI Handling for Claude API Calls

Clinical notes and images sent to Claude contain PHI. The following controls apply:

- **BAA with Anthropic is a prerequisite** — The system cannot process real patient data without an executed BAA. Development and testing use synthetic data only.
- **Minimum necessary standard** — Only the clinical information needed for the specific AI task is sent. Patient name, DOB, SSN, and insurance member IDs are stripped before API calls. The AI receives tooth numbers, procedures, conditions, and clinical findings — not patient identity.
- **No Anthropic data retention** — Claude API with BAA does not retain inputs/outputs for training. API calls use ephemeral processing only.
- **Local audit of all API calls** — Every request to Claude is logged locally (input hash, output, timestamp, prompt version) for compliance auditing. The actual PHI is logged in the local encrypted audit store, not in application logs.
- **Fallback if API unavailable** — If Claude API is unreachable, encounters queue for processing. The front desk can manually code using the CDT reference database. No claims are blocked from submission — manual coding is always available.

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

**Licensing:** CDT codes are copyrighted by the ADA. The system requires an ADA license for official descriptors (annual license fee). The code database is loaded from a configurable data source (JSON/CSV import) so licensed content is plugged in separately from the application code and is never committed to source control. The system is functional without official descriptors during development using code numbers and abbreviated descriptions only.

### Payer Intelligence Database

Per-insurance-company rules and patterns:
- Frequency limitations
- Age limitations
- Downcoding patterns
- Pre-authorization requirements
- Preferred narrative language
- Known bundling behavior

Initial manual curation for major payers: Delta Dental, MetLife, Cigna, Aetna, United Healthcare Dental, Guardian. Enriched over time from aggregated denial/approval patterns across tenants — aggregation uses only code-level outcomes (CDT code + payer + approved/denied), never patient-level data. Tenants must opt in to contribute anonymized data via a clear consent toggle in settings. This meets HIPAA Safe Harbor de-identification since no patient identifiers are included in the aggregate.

### Fee Schedule Management

- UCR (Usual, Customary, and Reasonable) fee schedules
- Per-payer contracted rates where available

### Knowledge Base Updates

- CDT codes update annually (effective January 1)
- Payer rules change frequently
- Admin interface for uploading new code sets
- Payer rules versioned with changelog

## Error Handling & Resilience

### Claude API Failures

- **Timeout/rate limit:** Requests retry with exponential backoff (3 attempts, 2s/4s/8s). After exhaustion, the encounter is queued with status `ai_pending` and the user is notified.
- **API outage:** The system degrades gracefully — manual coding is always available via the CDT reference database. A banner alerts users that AI features are temporarily unavailable.
- **Malformed response:** If Claude returns unparseable output, the request is retried with a simplified prompt. If it fails again, the encounter is flagged for manual coding with the raw AI response attached for debugging.

### Clearinghouse Submission Failures

- **Synchronous rejection (formatting errors):** The error is parsed, mapped to the offending claim field, and surfaced to the front desk user with a specific fix suggestion.
- **Asynchronous rejection (eligibility/coding):** Processed when the 277CA acknowledgment arrives. Denied claims route to the Denial Management module.
- **Connection failure:** Submissions retry 3 times with backoff. If all retries fail, the claim is queued with status `submission_failed` and the user is alerted. Claims approaching filing deadlines are flagged with high priority.

### Ingestion Pipeline Failures

- **Voice transcription failure:** The audio file is preserved. User is notified to retry or enter notes manually.
- **Image processing failure:** Images are stored and attached to the encounter. AI analysis is retried or skipped — the user can proceed with text-based coding.
- **Partial parsing:** If Claude extracts some but not all procedures from notes, the partial result is presented with a warning. The user completes the missing entries manually.

### Data Consistency

- **Database transactions:** All multi-step operations (e.g., code encounter + create claim) are wrapped in database transactions with rollback on failure.
- **Idempotency:** Claim submission and ERA processing are idempotent — duplicate submissions are detected and rejected. Each operation carries a unique idempotency key.

## Security & Compliance

### HIPAA Compliance

**Data protection:**
- All PHI encrypted at rest (AES-256) and in transit (TLS 1.3)
- Database-level encryption with per-tenant keys
- S3 server-side encryption for files
- BAA required with Anthropic (Claude API), AWS, and clearinghouse partners

**Authentication & access controls:**
- **Identity provider:** AWS Cognito with OAuth2/OIDC. Supports SAML federation for enterprise dental groups.
- **Token flow:** Cognito issues JWT access tokens (15 min TTL) + refresh tokens (30 day TTL). Backend validates JWT signature and extracts tenant_id + role from custom claims.
- Role-based access control (RBAC): dentist, hygienist, front desk, office admin
- Multi-factor authentication required (TOTP or SMS via Cognito)
- Session timeout after configurable inactivity (default 15 minutes)
- Row-level security — all database queries scoped by `tenant_id` extracted from JWT. Enforced at the ORM layer via a mandatory query filter, not optional per-query logic.

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
- **Row-level isolation** with a mandatory `tenant_id` column on all tenant-scoped tables. Enforced at the ORM/repository layer — every query passes through a tenant-scoping middleware that injects the tenant_id filter. This is simpler to operate than schema-per-tenant and scales well to thousands of tenants.
- Per-tenant encryption keys for file storage (S3 SSE with per-tenant KMS keys). Database encryption uses a shared RDS encryption key (per-tenant DB keys would require separate RDS instances, which is cost-prohibitive).
- Tenant-specific configuration for autonomy, payers, fee schedules

### Infrastructure

- **CI/CD:** GitHub Actions
- **Containers:** Docker, deployed via AWS ECS
- **Monitoring:** AWS CloudWatch for infrastructure metrics, Sentry for error tracking. Key dashboards: Claude API latency/error rates, claim submission success rates, AI confidence score distributions, failed auth attempts, PHI access anomalies
- **Backups:** Automated daily with point-in-time recovery, 30-day retention. RTO target: 4 hours. RPO target: 1 hour (via RDS continuous backup). Cross-region replication deferred to post-MVP.
- **Audit log storage:** Audit logs written to CloudWatch Logs with a restrictive resource policy (application role can write but not delete/modify). Provides tamper-evidence without relying on application-level hash chain alone.
- **Rate limiting:** Per-tenant rate limits on AI-triggering endpoints (`/coding/preview`, `/encounters/from-*`, `/denials/*/generate-appeal`) to manage Claude API costs. Default: 60 AI requests/minute per tenant. Configurable per plan tier.
- **API versioning:** All endpoints prefixed with `/v1/`. Breaking changes require a new version prefix.
