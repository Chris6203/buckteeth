# Phenomenal Problems (Buckteeth)

AI-powered dental insurance coding and revenue cycle management platform.

**Live:** https://phenomenalproblems.com

## What It Does

Buckteeth takes clinical input in any form — structured data, free-text notes, voice dictation, or x-rays — and:

1. **Parses** clinical documentation into structured procedure data
2. **Codes** procedures with the correct CDT codes (and ICD-10 for medical cross-coding)
3. **Validates** codes against payer rules for frequency limits, bundling, and age restrictions
4. **Builds** complete insurance claims with narratives and attachments
5. **Submits** claims through clearinghouses or generates ADA dental claim forms
6. **Predicts** denial risk before submission and suggests proactive fixes
7. **Manages** denials with AI-generated payer-specific appeal letters citing case law
8. **Sends** formal complaint letters to state insurance commissioners via physical mail
9. **Tracks** the full revenue cycle from coding through payment posting

## Who It's For

- **Dentists/Hygienists** — document procedures and review AI-suggested codes
- **Front Desk/Insurance Coordinators** — manage claims, handle denials, track payments

## Tech Stack

- **Backend:** Python 3.11+ (FastAPI, SQLAlchemy 2.0 async, Pydantic v2) — 79 files, 17,316 lines
- **Frontend:** React 18 (TypeScript, Vite, Tailwind CSS, React Router v6) — 23 files
- **Database:** PostgreSQL 16 (async via asyncpg; 18 tables)
- **AI:** Claude (Anthropic SDK) — coding suggestions, appeal generation, risk assessment
- **PDF:** ReportLab (ADA dental claim forms)
- **EDI:** X12 837D, 270/271, 835 (HIPAA-compliant dental claim processing)
- **Auth:** JWT tokens, role-based access (admin, provider, staff)
- **Deployment:** Ubuntu server, nginx, systemd, Let's Encrypt SSL

## Architecture

Modular monolith with clear module boundaries and multi-tenant row-level isolation:

| Module | Purpose |
|--------|---------|
| Auth | JWT registration, login, role-based access (admin/provider/staff) |
| Ingestion | Normalize clinical input (text, voice, images) via Claude Vision + transcription |
| Coding Engine | AI-powered CDT/ICD-10 code selection with RAG from 315-code CDT knowledge base |
| Claim Builder | Assemble claims with AI-generated payer-specific narratives |
| Submission Gateway | Route claims to clearinghouses with idempotent retry |
| Denial Management | Predict denials, generate payer-specific appeals citing case law, send commissioner letters |
| Denial Feedback | Learn from prior denials, track patterns per payer, auto-update rules |
| EDI Layer | X12 837D claims, 270/271 eligibility, 835 ERA parsing (50 CARC codes), 26-payer directory |
| Pre-Submission Validation | Check frequency rules, documentation, preauth, benefits before submitting |
| Image Verification | Claude Vision verifies X-rays/photos support coded procedures |
| Coding Update Agent | Monitors 7 sources for CDT/payer rule changes, AI-powered analysis |
| PMS Adapters | Integrate with practice management systems (Open Dental, CSV import/export) |
| Dashboard | React PWA with voice dictation, image upload, mobile-responsive dark theme |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15+ (or SQLite for development)
- An Anthropic API key

### Backend Setup

```bash
# Clone the repo
git clone https://github.com/Chris6203/buckteeth.git
cd buckteeth

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your database URL and API key

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn buckteeth.main:app --reload
```

The API server runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API requests to the backend.

### Running Tests

```bash
# Backend tests (138 tests)
pytest tests/ -v

# Frontend tests (13 tests)
cd frontend && npm test
```

## API Endpoints

61 REST endpoints across 13 modules, all under the `/v1` prefix (plus health check):

### Auth (`/v1/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/register` | Register a new user |
| POST | `/v1/auth/login` | Login, returns JWT token |
| GET | `/v1/auth/me` | Get current authenticated user |
| POST | `/v1/auth/invite` | Invite a user (admin only) |

### Patients (`/v1/patients`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/patients` | Create a patient |
| GET | `/v1/patients` | List patients (supports `?q=` search) |
| GET | `/v1/patients/{id}` | Get a patient |
| GET | `/v1/patients/{id}/insurance` | List insurance plans |
| POST | `/v1/patients/{id}/insurance` | Add insurance plan |
| DELETE | `/v1/patients/{id}/insurance/{plan_id}` | Remove insurance plan |

### Encounters (`/v1/encounters`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/encounters/from-notes` | Parse clinical notes into structured encounter |
| POST | `/v1/encounters/from-image` | Analyze x-ray/photo via Claude Vision |
| POST | `/v1/encounters/from-voice` | Transcribe audio and parse encounter |
| POST | `/v1/encounters/check-image-quality` | Check image quality before processing |
| GET | `/v1/encounters/{id}` | Get an encounter |
| POST | `/v1/encounters/{id}/verify-images` | Verify image supports coded procedures (AI Vision) |
| POST | `/v1/encounters/{id}/check-documentation` | Check documentation completeness |
| POST | `/v1/encounters/{id}/documentation-template` | Get smart documentation template |
| POST | `/v1/encounters/{id}/validate` | Full pre-submission validation |

### Coding (`/v1/encounters`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/encounters/{id}/code` | AI-suggest CDT codes for encounter |
| GET | `/v1/encounters/{id}/coded` | Get coded encounter |
| POST | `/v1/encounters/{id}/coded/approve` | Approve AI-suggested codes |

### Claims (`/v1/claims`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/claims` | Build claim from coded encounter |
| GET | `/v1/claims` | List claims (filterable by status) |
| GET | `/v1/claims/{id}` | Get a claim with procedures and narratives |
| PUT | `/v1/claims/{id}/status` | Update claim status |
| POST | `/v1/claims/{id}/assess-risk` | AI denial risk assessment |
| GET | `/v1/claims/{id}/pdf` | Download ADA claim form PDF |

### Submissions (`/v1/submissions`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/submissions/submit` | Submit claim to clearinghouse |
| POST | `/v1/submissions/batch-submit` | Batch submit multiple claims |
| GET | `/v1/submissions` | List submissions |
| GET | `/v1/submissions/{id}` | Get submission status |
| POST | `/v1/submissions/eligibility` | Check patient insurance eligibility |

### Denials (`/v1/denials`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/denials` | Record a denial |
| GET | `/v1/denials` | List denials (filterable by status) |
| GET | `/v1/denials/{id}` | Get a denial |
| POST | `/v1/denials/{id}/generate-appeal` | AI-generate payer-specific appeal letter |
| POST | `/v1/denials/{id}/send-commissioner-letter` | Generate and mail commissioner complaint |
| GET | `/v1/denials/{id}/commissioner-letters` | List commissioner letters for a denial |

### Settings (`/v1/settings`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/settings` | Get practice settings |
| PUT | `/v1/settings` | Update practice settings |

### Updates (`/v1/updates`) — Coding Update Agent
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/updates/check` | Check for coding updates from 7 sources |
| GET | `/v1/updates/sources` | List monitored update sources |
| GET | `/v1/updates/status` | Get update status |
| POST | `/v1/updates/{title}/apply` | Mark an update as applied |

### Providers (`/v1/providers`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/providers` | Create a provider |
| GET | `/v1/providers` | List providers |
| GET | `/v1/providers/{id}` | Get a provider |
| PUT | `/v1/providers/{id}` | Update a provider |
| DELETE | `/v1/providers/{id}` | Deactivate a provider |

### PMS Integration (`/v1/pms`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/pms/status` | Check PMS connection status |
| GET | `/v1/pms/patients` | List patients from PMS |
| GET | `/v1/pms/patients/{id}/encounters` | Get treatment history from PMS |
| POST | `/v1/pms/import-patient` | Import patient from PMS into Buckteeth |
| POST | `/v1/pms/import-encounter` | Import encounter from PMS into Buckteeth |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

## Project Structure

```
src/buckteeth/                     # 77 Python files, 16,279 lines
├── main.py              # FastAPI app entrypoint + CORS
├── config.py            # Settings (Pydantic)
├── database.py          # Async SQLAlchemy engine and session
├── auth.py              # JWT authentication, password hashing, role checks
├── tenant.py            # Multi-tenant context
├── models/              # SQLAlchemy models (9 modules)
│   ├── base.py          # Base model
│   ├── patient.py       # Patient + insurance plans
│   ├── encounter.py     # Clinical encounters + procedures
│   ├── coding.py        # Coded encounters + procedures
│   ├── claim.py         # Claims + procedures + narratives + attachments
│   ├── denial.py        # Denials + appeals + commissioner letters
│   ├── submission.py    # Submissions + ERA records
│   ├── user.py          # Users (registration, roles, JWT)
│   └── audit.py         # Audit logs
├── api/                 # REST API routers and Pydantic schemas (12 modules)
│   ├── deps.py          # Shared dependencies (tenant, session)
│   ├── schemas.py       # All request/response schemas
│   ├── auth.py          # Register, login, invite, current user
│   ├── patients.py      # Patient CRUD + insurance plans
│   ├── encounters.py    # Encounter parsing (text, image, voice, quality check)
│   ├── coding.py        # AI coding engine endpoints
│   ├── claims.py        # Claim building, risk assessment, PDF
│   ├── submissions.py   # Clearinghouse submission
│   ├── denials.py       # Appeals, commissioner letters
│   ├── settings.py      # Practice settings CRUD
│   ├── updates.py       # Coding update agent endpoints
│   └── pms.py           # PMS sync endpoints
├── ingestion/           # Clinical input parsing + image analysis + quality + transcription
├── coding/              # AI coding engine, image verifier, doc checker, pre-submission validator,
│                        #   documentation_templates, update_agent
├── claims/              # Claim narrative generation
├── submission/          # Clearinghouse adapter pattern + gateway
├── denials/             # Appeal generator, commissioner letters, risk scorer, feedback engine
├── forms/               # ADA dental claim form PDF generation (ReportLab)
├── edi/                 # X12 837D, 270/271, 835, payer directory, clearinghouse adapters
├── pms/                 # PMS adapters (Mock, Open Dental, CSV)
└── knowledge/           # CDT codes (315), payer rules, case law repository

frontend/                # 23 TypeScript/TSX files
├── src/
│   ├── App.tsx          # Router
│   ├── main.tsx         # Entry point
│   ├── speech.d.ts      # Web Speech API types
│   ├── api/             # Typed fetch client + TypeScript interfaces
│   │   ├── client.ts    # API functions for all endpoints
│   │   └── types.ts     # TypeScript types matching backend schemas
│   ├── components/      # Shared UI components
│   │   ├── Layout.tsx       # Sidebar navigation shell
│   │   ├── StatusBadge.tsx  # Color-coded status pill
│   │   ├── ToothChart.tsx   # Interactive 32-tooth chart
│   │   ├── BenefitsEntry.tsx # Insurance benefits entry
│   │   ├── PerioChart.tsx   # Periodontal charting
│   │   └── ErrorBoundary.tsx # Crash fallback UI
│   ├── pages/           # Route pages
│   │   ├── Dashboard.tsx    # Dollar totals, recent activity
│   │   ├── Encounters.tsx   # Core workflow: dictate/image → AI coding → validation → claim
│   │   ├── Patients.tsx     # Patient list + search + create + insurance
│   │   ├── Claims.tsx       # Expandable procedures, summary totals
│   │   ├── Denials.tsx      # Card layout, 3-stage appeal workflow
│   │   └── Setup.tsx        # Practice settings (persists to backend)
│   └── __tests__/       # Vitest + React Testing Library tests
├── index.html
├── vite.config.ts       # Vite config with API proxy + Vitest
├── tailwind.config.js
└── package.json

tests/                   # Backend tests (pytest, async)
├── conftest.py          # Shared fixtures (engine, db_session)
├── api/                 # API integration tests
├── models/              # Model unit tests
├── ingestion/           # Ingestion tests
├── coding/              # Coding engine tests
├── claims/              # Claims tests
├── submission/          # Submission tests
├── denials/             # Denial management tests
├── forms/               # PDF generation tests
├── pms/                 # PMS adapter tests
└── knowledge/           # Knowledge base tests
```

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation — models, multi-tenancy, patient/encounter APIs | Done |
| 2 | Claim Builder — AI narratives, claim assembly | Done |
| 3 | Submission Gateway — clearinghouse adapters, eligibility | Done |
| 4 | Denial Management — appeals, commissioner letters, mail | Done |
| 5 | Advanced Ingestion & Risk — image analysis, voice, risk scoring, PDF forms | Done |
| 6 | PMS Adapters — Open Dental, CSV import/export, sync API | Done |
| 7 | React Dashboard — frontend with patients, claims, denials pages | Done |
| 8 | Phenomenal Problems — rebranding, dark theme, mobile PWA, voice dictation | Done |
| 9 | EDI Insurance Layer — X12 837D/270/271/835, 26-payer directory, clearinghouse adapters | Done |
| 10 | Denial Prevention — image verification, doc checker, pre-submission validator, feedback engine | Done |
| 11 | Auth & Updates — JWT auth (register/login/roles), coding update agent (7 sources), practice settings | Done |
| 12 | Appeal Workflow — payer-specific appeals, preview/edit/approve, card-based denials UI | Done |

## Documentation

- [Complete System Documentation](docs/DEMO-CHECKLIST.md)
- [Design Spec](docs/superpowers/specs/2026-03-12-dental-coding-agent-design.md)
- [Phase 1 Plan: Foundation](docs/superpowers/plans/2026-03-12-phase1-foundation.md)
- [Phase 2 Plan: Claim Builder](docs/superpowers/plans/2026-03-12-phase2-claim-builder.md)
- [Phase 3 Plan: Submission Gateway](docs/superpowers/plans/2026-03-12-phase3-submission-gateway.md)
- [Phase 4 Plan: Denial Management](docs/superpowers/plans/2026-03-12-phase4-denial-management.md)
- [Phase 5 Plan: Advanced Ingestion & Risk](docs/superpowers/plans/2026-03-12-phase5-advanced-ingestion-risk.md)
- [Phase 6 Plan: PMS Adapters](docs/superpowers/plans/2026-03-13-phase6-pms-adapters.md)
- [Phase 7 Plan: React Dashboard](docs/superpowers/plans/2026-03-13-phase7-react-dashboard.md)

## License

Proprietary. All rights reserved.
