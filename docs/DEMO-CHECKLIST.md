# Phenomenal Problems — Complete System Documentation

**Live at:** https://phenomenalproblems.com
**Dev access:** http://65.38.96.145/bt/
**Server:** 65.38.96.145 (Ubuntu, nginx, PostgreSQL 16)

---

## System Overview

Phenomenal Problems is an AI-powered dental insurance coding and revenue cycle management platform. It automates clinical note parsing, CDT code selection, claim generation, denial prevention, and appeal generation — all powered by Claude AI.

### How It Works (Demo Flow)

1. Dentist opens the app on a tablet
2. Selects a patient and taps **Dictate**
3. Speaks naturally: *"Patient presents with deep caries on #19, MOD involvement. Crown prep with core buildup."*
4. Optionally attaches an X-ray photo
5. Taps **Process with AI** — the system:
   - Parses clinical notes into structured procedures
   - Suggests CDT codes with confidence scores
   - Checks documentation completeness (flags missing X-rays)
   - Runs pre-submission validation (frequency limits, preauth, denial patterns)
   - If image attached: verifies it supports the coded procedures
6. Dentist reviews, taps **Approve & Generate Claim**
7. Claim is created with proper codes, fees, and narratives

---

## What's Built

### Infrastructure
- [x] FastAPI backend (uvicorn, port 8000, systemd managed)
- [x] React + TypeScript + Vite frontend (dark theme, cyan/navy branding)
- [x] PostgreSQL 16 database with demo data (18 tables)
- [x] Nginx reverse proxy (domain + IP path routing)
- [x] HTTPS with Let's Encrypt (auto-renewing, expires June 2026)
- [x] Domain: phenomenalproblems.com (DNS via GoDaddy)
- [x] PWA manifest (installable on tablet home screen)
- [x] Mobile-responsive layout (collapsible sidebar, touch-friendly)
- [x] Marketing landing page at phenomenalproblems.com root

### Authentication & Authorization
- [x] User registration (`POST /v1/auth/register`)
- [x] Login with JWT tokens (`POST /v1/auth/login`)
- [x] Current user info (`GET /v1/auth/me`)
- [x] User invitation system (`POST /v1/auth/invite`)
- [x] Role-based access: admin, provider, staff

### Frontend Pages (6)
- [x] **Dashboard** — dollar totals, recent activity, how-it-works guide, what AI catches, setup checklist (auto-opens if incomplete)
- [x] **New Encounter** — dictate/type/image → AI coding → smart doc templates → validation → claim
- [x] **Patients** — list with initials avatars, insurance plan management, tooth chart, benefits entry, patient search (`GET /v1/patients?q=`)
- [x] **Claims** — list with status filters, expandable procedures, summary totals, patient names, risk assessment
- [x] **Denials** — card layout with 3-stage appeal workflow (generate → preview/edit → approve), payer-specific appeal generation with addresses, deadlines, strategies
- [x] **Practice Setup** — provider info, fee schedule (33 codes), clearinghouse config, setup status, settings persist to backend

### Frontend Components
- [x] **Tooth Chart** — interactive 32-tooth chart, mark missing teeth with extraction dates
- [x] **Benefits Entry** — annual max, used, remaining, deductible, coverage percentages
- [x] **Perio Chart** — simplified 3-point pocket depth entry per tooth, color-coded by severity
- [x] **Error Boundary** — catches crashes, shows friendly fallback UI
- [x] **Searchable patient dropdown** in encounters
- [x] **Dismissible how-it-works** card (persists via localStorage)

### AI Features (all powered by Claude)
- [x] Clinical note parsing (text → structured procedures with teeth, surfaces, diagnoses)
- [x] Dental image analysis (X-rays, radiographs, photos via Claude Vision)
- [x] CDT code suggestion with confidence scores and AI reasoning (RAG + Claude)
- [x] Image-procedure verification (does the X-ray support the coded procedure?)
- [x] Documentation completeness checking (flags missing X-rays, narratives, perio charting)
- [x] Claim narrative generation (payer-tailored medical necessity justifications)
- [x] Denial risk scoring (rule-based + Claude analysis)
- [x] Payer-specific appeal letter generation with payer addresses, deadlines, and strategies
- [x] Appeal preview/edit/approve workflow in frontend
- [x] Commissioner complaint letter generation (all 50 states + DC)

### Voice Input
- [x] Browser speech recognition (Web Speech API)
- [x] Auto-restarts on silence (Chrome tends to stop listening)
- [x] Real-time interim text display while speaking
- [x] Works on Chrome (desktop/Android) and Safari (iOS/Mac)
- [x] Requires HTTPS (works on domain, not on HTTP IP)

### Pre-Submission Validation Engine (694 lines)
- [x] Documentation requirements (100+ CDT codes mapped to required X-rays, narratives, perio charting)
- [x] Payer frequency rules (26 payers, code-specific limits)
- [x] Pre-authorization flagging
- [x] Benefit/eligibility checks (when data available)
- [x] Known denial pattern matching
- [x] 10+ coding bundling rules (prophy+SRP, FMX+BWX, core+crown, etc.)
- [x] Age limitation checks (sealants, child prophy, ortho, etc.)
- [x] Timely filing deadline warnings (90-365 days by payer type)
- [x] Waiting period reminders for major procedures
- [x] Missing tooth clause reminders for bridges/dentures
- [x] SRP-specific 90% denial warning without perio charting
- [x] Crown narrative guidance (% compromised, failure reason, alternatives)
- [x] Coordination of benefits reminders
- [x] Per-issue denial probability percentage
- [x] Overall denial risk score

### Smart Documentation Templates
- [x] Auto-detects procedures from parsed notes and generates specific prompts
- [x] Crown: periapical X-ray, % structure compromised, restoration failure reason
- [x] SRP: bitewing X-rays, perio charting with pocket depths, AAP diagnosis, bone loss pattern
- [x] Root Canal: periapical X-ray, pulp diagnosis (AAE), periapical diagnosis, vitality tests
- [x] Extraction: periapical X-ray, reason for extraction
- [x] Implant: panoramic + periapical X-ray, treatment plan, date of tooth loss
- [x] Denture: panoramic X-ray, missing teeth with dates

### CDT Knowledge Base (315 codes, CDT 2026 current)
- [x] 315 CDT codes across all 11 categories (includes D0270 added)
- [x] CDT 2026 updates: D1352 deleted, D2391 revised, D9230 revised, D5876 revised
- [x] CDT 2026 new codes: D0418 saliva testing, D0419 cracked tooth, D5115/D5125 backup dentures, D9947 guard cleaning
- [x] Each code has: common scenarios, confusion codes, bundling notes, frequency notes, denial reasons
- [x] Crown code RAG retrieval fixed (keyword boosting)
- [x] Verified against ADA official sources

### Insurance Integration Layer (EDI)
- [x] **X12 837D Generator** (1,051 lines) — HIPAA-compliant dental claim format
- [x] **X12 270/271** (538 lines) — eligibility request/response
- [x] **X12 835 Parser** — ERA payment/denial parsing, **50 CARC codes** (verified against X12.org), 20 RARC codes
- [x] **Payer Directory** — 26 dental payers, alternate IDs, verified flag (4/26 verified against official sources)
- [x] **Clearinghouse Adapters** — Claim.MD (full), DentalXChange/Availity/Tesia/Change Healthcare (stubs)

### Accuracy Verification (completed 2026-03-23)
- [x] CARC codes expanded from 27 to 50, verified against X12.org official definitions — 8 corrections made
- [x] MetLife payer ID corrected: 65978 → 61109 (65978 kept as alternate)
- [x] Guardian payer ID: GI813 added as alternate
- [x] Aetna DMO alternate ID 68246 added
- [x] Cigna 62308, Aetna 60054, UHC 87726, MetLife 61109 verified against official sources

### Coding Update Agent
- [x] Monitors 7 sources (ADA, Delta Dental, Cigna, MetLife, UHC, CMS, ADA News)
- [x] CDT 2026 updates pre-loaded (9 known changes tracked)
- [x] AI-powered content analysis for new updates
- [x] Persistent update history
- [x] API endpoints: check for updates, list sources, get status, mark applied

### Denial Feedback Learning System
- [x] Ingests denials and extracts patterns per payer
- [x] 48 CARC code → actionable rule mappings
- [x] Auto-derives rules from denial reason codes
- [x] Warns on future claims when patterns match
- [x] Practice-level reporting (worst payers, most denied codes, revenue impact)
- [x] Trend tracking (improving/worsening/stable)

### Bug Fixes Applied
- [x] Create patient lazy load bug fixed
- [x] Crown code RAG retrieval fixed (keyword boosting)
- [x] Appeal generator was using placeholder API key — fixed
- [x] Appeal generator JSON parsing — markdown fences handling fixed

---

## Architecture

```
Browser / Tablet (PWA)
    ↓ HTTPS
Nginx (port 80/443)
    ├─ /bt/*                        → Frontend (React SPA)
    ├─ /bt/v1/*                     → FastAPI backend (port 8000)
    ├─ phenomenalproblems.com/bt/*  → Same (domain route)
    └─ /*                           → Marketing landing page / SmileTryte app (port 3000)

FastAPI Backend (port 8000) — 77 Python files, 16,279 lines
    ├─ Auth Layer
    │   ├─ JWT token authentication
    │   ├─ Role-based access (admin, provider, staff)
    │   └─ User registration + invitation
    ├─ AI Layer
    │   ├─ Claude API — note parsing, coding, narratives, appeals, image analysis
    │   ├─ CDT Code Repository (RAG knowledge base, 315 codes)
    │   ├─ Case Law Repository
    │   └─ Payer Rules Repository
    ├─ Validation Layer
    │   ├─ Pre-submission validator
    │   ├─ Documentation checker
    │   ├─ Image-procedure verifier (Claude Vision)
    │   └─ Denial feedback engine
    ├─ EDI Layer
    │   ├─ X12 837D claim generator
    │   ├─ X12 270/271 eligibility
    │   ├─ X12 835 ERA parser (50 CARC codes)
    │   ├─ Payer directory (26 payers)
    │   └─ Clearinghouse adapters
    ├─ Coding Update Agent (7 monitored sources)
    ├─ PostgreSQL 16
    │   └─ 18 tables (patients, encounters, claims, denials, users, etc.)
    └─ Mock Adapters (PMS, clearinghouse)
```

---

## API Endpoints (51 total)

### Auth
- `POST /v1/auth/register` — Register new user
- `POST /v1/auth/login` — Login, returns JWT token
- `GET /v1/auth/me` — Get current authenticated user
- `POST /v1/auth/invite` — Invite a user (admin only)

### Encounters
- `POST /v1/encounters/from-notes` — Parse clinical notes (AI)
- `POST /v1/encounters/from-image` — Analyze dental image (AI + Vision)
- `POST /v1/encounters/from-voice` — Transcribe + parse audio
- `POST /v1/encounters/check-image-quality` — Check image quality before processing
- `GET /v1/encounters/{id}` — Get encounter
- `POST /v1/encounters/{id}/verify-images` — Verify image supports procedures (AI)
- `POST /v1/encounters/{id}/check-documentation` — Check documentation completeness
- `POST /v1/encounters/{id}/documentation-template` — Get smart documentation template
- `POST /v1/encounters/{id}/validate` — Full pre-submission validation

### Coding
- `POST /v1/encounters/{id}/code` — AI suggest CDT codes
- `GET /v1/encounters/{id}/coded` — Get coded encounter
- `POST /v1/encounters/{id}/coded/approve` — Approve codes

### Patients
- `POST /v1/patients` — Create patient
- `GET /v1/patients` — List patients (supports `?q=` search)
- `GET /v1/patients/{id}` — Get patient
- `GET /v1/patients/{id}/insurance` — List insurance plans
- `POST /v1/patients/{id}/insurance` — Add insurance plan
- `DELETE /v1/patients/{id}/insurance/{plan_id}` — Remove insurance plan

### Claims
- `POST /v1/claims` — Create claim from coded encounter
- `GET /v1/claims` — List claims (filterable by status)
- `GET /v1/claims/{id}` — Get claim
- `PUT /v1/claims/{id}/status` — Update status
- `POST /v1/claims/{id}/assess-risk` — AI denial risk assessment
- `GET /v1/claims/{id}/pdf` — Download ADA claim form PDF

### Submissions
- `POST /v1/submissions/submit` — Submit claim to clearinghouse
- `POST /v1/submissions/batch-submit` — Batch submit
- `GET /v1/submissions` — List submissions
- `GET /v1/submissions/{id}` — Get submission
- `POST /v1/submissions/eligibility` — Check eligibility

### Denials
- `POST /v1/denials` — Record denial
- `GET /v1/denials` — List denials
- `GET /v1/denials/{id}` — Get denial
- `POST /v1/denials/{id}/generate-appeal` — AI appeal letter (payer-specific)
- `POST /v1/denials/{id}/send-commissioner-letter` — Commissioner complaint
- `GET /v1/denials/{id}/commissioner-letters` — List letters

### Settings
- `GET /v1/settings` — Get practice settings
- `PUT /v1/settings` — Update practice settings

### Updates (Coding Update Agent)
- `POST /v1/updates/check` — Check for coding updates
- `GET /v1/updates/sources` — List monitored sources
- `GET /v1/updates/status` — Get update status
- `POST /v1/updates/{title}/apply` — Mark update as applied

### PMS Integration
- `GET /v1/pms/status` — Check PMS connection status
- `GET /v1/pms/patients` — List patients from PMS
- `GET /v1/pms/patients/{id}/encounters` — Get treatment history from PMS
- `POST /v1/pms/import-patient` — Import patient from PMS
- `POST /v1/pms/import-encounter` — Import encounter from PMS

### System
- `GET /health` — Health check

---

## Payers Supported (26)

**Delta Dental:** CA, NY, PA, TX, IL, WA, MI, MA
**Major Commercial:** MetLife (61109, alt 65978), Cigna (62308), Aetna (60054, alt 68246), Guardian (GI813 alt), UHC (87726), Humana, Principal, Ameritas, Lincoln Financial, Sun Life, Anthem BCBS
**Government:** GEHA, TRICARE
**Medicaid:** DentaQuest, MCNA, Liberty Dental
**Other:** Dental Health Alliance, Connection Dental

Each payer has: real EDI payer ID, frequency rules per CDT code, pre-auth requirements, common denial codes.

---

## File Structure

```
/opt/buckteeth/                    # Production deployment
├── src/buckteeth/                 # 77 Python files, 16,279 lines
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings (DATABASE_URL, API keys)
│   ├── database.py                # Async SQLAlchemy
│   ├── auth.py                    # JWT authentication, password hashing, role checks
│   ├── tenant.py                  # Multi-tenant context
│   ├── api/                       # API routes (12 modules)
│   │   ├── deps.py                # Shared dependencies (tenant, session)
│   │   ├── schemas.py             # All request/response schemas
│   │   ├── auth.py                # Register, login, invite, me
│   │   ├── patients.py            # Patient CRUD + insurance plans
│   │   ├── encounters.py          # Encounter parsing (text, image, voice, quality check)
│   │   ├── coding.py              # AI coding engine endpoints
│   │   ├── claims.py              # Claim building, risk assessment, PDF
│   │   ├── submissions.py         # Clearinghouse submission
│   │   ├── denials.py             # Appeals, commissioner letters
│   │   ├── settings.py            # Practice settings
│   │   ├── updates.py             # Coding update agent endpoints
│   │   └── pms.py                 # PMS sync endpoints
│   ├── models/                    # SQLAlchemy models (9 modules)
│   │   ├── base.py                # Base model
│   │   ├── patient.py             # Patient + insurance plans
│   │   ├── encounter.py           # Clinical encounters + procedures
│   │   ├── coding.py              # Coded encounters + procedures
│   │   ├── claim.py               # Claims + procedures + narratives + attachments
│   │   ├── denial.py              # Denials + appeals + commissioner letters
│   │   ├── submission.py          # Submissions + ERA records
│   │   ├── user.py                # Users (auth, roles)
│   │   └── audit.py               # Audit logs
│   ├── ingestion/                 # Text parser, image analyzer, image quality, transcription
│   ├── coding/                    # CDT selector, image verifier, doc checker, validator,
│   │                              #   documentation_templates, update_agent
│   ├── claims/                    # Claim builder, narrative generator
│   ├── denials/                   # Appeal generator, risk scorer, commissioner, feedback engine
│   ├── submission/                # Gateway, clearinghouse adapters
│   ├── knowledge/                 # CDT codes (315), case law, payer rules (RAG)
│   ├── edi/                       # X12 837D, 270/271, 835, payer directory, clearinghouse adapters
│   ├── pms/                       # PMS adapters (mock, future: Open Dental, Dentrix)
│   └── forms/                     # ADA claim form PDF generator
├── frontend/                      # 23 TypeScript/TSX files
│   ├── src/
│   │   ├── App.tsx                # Router
│   │   ├── main.tsx               # Entry point
│   │   ├── speech.d.ts            # Web Speech API types
│   │   ├── components/
│   │   │   ├── Layout.tsx         # Responsive sidebar + mobile header
│   │   │   ├── StatusBadge.tsx    # Color-coded status pill
│   │   │   ├── ToothChart.tsx     # Interactive 32-tooth chart
│   │   │   ├── BenefitsEntry.tsx  # Insurance benefits entry
│   │   │   ├── PerioChart.tsx     # Periodontal charting
│   │   │   └── ErrorBoundary.tsx  # Crash fallback UI
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # Dollar totals, recent activity, setup checklist
│   │   │   ├── Encounters.tsx     # Core workflow: dictate/image → AI → claim
│   │   │   ├── Patients.tsx       # Patient list + search + create + insurance
│   │   │   ├── Claims.tsx         # Expandable procedures, summary totals
│   │   │   ├── Denials.tsx        # Card layout, 3-stage appeal workflow
│   │   │   └── Setup.tsx          # Practice settings (persists to backend)
│   │   ├── api/
│   │   │   ├── client.ts          # Typed API client
│   │   │   └── types.ts           # TypeScript types
│   │   └── __tests__/             # Vitest + React Testing Library tests
│   └── dist/                      # Production build
├── .env                           # DATABASE_URL, ANTHROPIC_API_KEY, ALLOWED_ORIGINS
├── alembic/                       # Database migrations
└── scripts/seed_demo.py           # Demo data seeder
```

```
/home/chris/buckteeth/             # Source / development copy
```

---

## Database Tables (18)

alembic_version, appeal_documents, audit_logs, claim_attachments, claim_narratives, claim_procedures, claims, clinical_encounters, clinical_procedures, coded_encounters, coded_procedures, commissioner_letters, denial_records, era_records, insurance_plans, patients, submission_records, users

---

## Useful Commands

```bash
# ── Service Management ──
sudo systemctl status buckteeth        # Check status
sudo systemctl restart buckteeth       # Restart after backend changes
sudo journalctl -u buckteeth -f        # Stream logs

# ── Frontend Build & Deploy ──
# 1. Edit files in /home/chris/buckteeth/frontend/src/
# 2. Copy to production:
sudo cp /home/chris/buckteeth/frontend/src/<file> /opt/buckteeth/frontend/src/<file>
# 3. Build:
cd /opt/buckteeth/frontend && sudo node_modules/.bin/vite build
# (No restart needed — nginx serves static files)

# ── Backend Deploy ──
# 1. Edit files in /home/chris/buckteeth/src/buckteeth/
# 2. Copy to production:
sudo cp /home/chris/buckteeth/src/buckteeth/<file> /opt/buckteeth/src/buckteeth/<file>
# 3. Restart:
sudo systemctl restart buckteeth

# ── Database ──
sudo -u buckteeth psql -U buckteeth -d buckteeth   # Connect
# Re-seed demo data:
cd /home/chris/buckteeth && PYTHONPATH=src /opt/buckteeth/.venv/bin/python3 scripts/seed_demo.py

# ── System Stats ──
# Count endpoints:
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import sys,json; paths=json.load(sys.stdin).get('paths',{}); print(sum(len([m for m in methods if m in ('get','post','put','delete')]) for methods in paths.values()))"
# Count CDT codes:
PYTHONPATH=/home/chris/buckteeth/src /opt/buckteeth/.venv/bin/python3 -c "from buckteeth.knowledge.cdt_codes import CDTCodeRepository; print(len(CDTCodeRepository()._codes))"
# Count CARC codes:
PYTHONPATH=/home/chris/buckteeth/src /opt/buckteeth/.venv/bin/python3 -c "from buckteeth.edi.x12_835 import CARC_CODES; print(len(CARC_CODES))"

# ── Nginx ──
sudo nginx -t && sudo systemctl reload nginx
sudo tail -f /var/log/nginx/error.log

# ── SSL Certificate ──
# Auto-renews via certbot. Check:
sudo certbot certificates
# Manual renew if needed:
sudo certbot renew
```

---

## Environment Variables (/opt/buckteeth/.env)

```
DATABASE_URL=postgresql+asyncpg://buckteeth:<password>@localhost:5432/buckteeth
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=https://phenomenalproblems.com,https://www.phenomenalproblems.com
LOG_LEVEL=INFO
```

---

## What's Next (Roadmap)

### Phase 1: Demo Ready (DONE)
Everything above.

### Phase 2: Real Clearinghouse Connection
- [ ] Sign up for Claim.MD developer account
- [ ] Configure ClaimMDAdapter with real credentials
- [ ] Enable real-time eligibility checks (270/271)
- [ ] Enable automatic ERA ingestion (835) → feeds denial learning engine
- [ ] Enable real claim submission (837D)

### Phase 3: PMS Integration
- [ ] Build Open Dental adapter (most common dental PMS)
- [ ] Build Dentrix adapter
- [ ] Auto-import patients and encounters
- [ ] Sync claim status back to PMS

### Phase 4: Scale
- [ ] Multi-practice support (tenant management UI)
- [ ] Audit logging dashboard
- [ ] Automated nightly eligibility batch checks
- [ ] Dashboard analytics (revenue recovered, denial rate trends)
