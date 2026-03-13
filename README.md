# Buckteeth

AI-powered dental insurance coding and revenue cycle management platform.

## What It Does

Buckteeth takes clinical input in any form — structured data, free-text notes, voice dictation, or x-rays — and:

1. **Parses** clinical documentation into structured procedure data
2. **Codes** procedures with the correct CDT codes (and ICD-10 for medical cross-coding)
3. **Validates** codes against payer rules for frequency limits, bundling, and age restrictions
4. **Builds** complete insurance claims with narratives and attachments
5. **Submits** claims through clearinghouses or generates ADA dental claim forms
6. **Predicts** denial risk before submission and suggests proactive fixes
7. **Manages** denials with AI-generated appeal letters citing case law
8. **Sends** formal complaint letters to state insurance commissioners via physical mail
9. **Tracks** the full revenue cycle from coding through payment posting

## Who It's For

- **Dentists/Hygienists** — document procedures and review AI-suggested codes
- **Front Desk/Insurance Coordinators** — manage claims, handle denials, track payments

## Tech Stack

- **Backend:** Python 3.11+ (FastAPI, SQLAlchemy 2.0 async, Pydantic v2)
- **Frontend:** React 18 (TypeScript, Vite, Tailwind CSS, React Router v6)
- **Database:** PostgreSQL 15+ (async via asyncpg; SQLite for tests)
- **AI:** Claude (Anthropic SDK) — coding suggestions, appeal generation, risk assessment
- **PDF:** ReportLab (ADA dental claim forms)
- **Auth:** AWS Cognito (planned)
- **Deployment:** Docker / AWS ECS (planned)

## Architecture

Modular monolith with clear module boundaries and multi-tenant row-level isolation:

| Module | Purpose |
|--------|---------|
| Ingestion | Normalize clinical input (text, voice, images) via Claude Vision + transcription |
| Coding Engine | AI-powered CDT/ICD-10 code selection with RAG from CDT knowledge base |
| Claim Builder | Assemble claims with AI-generated payer-specific narratives |
| Submission Gateway | Route claims to clearinghouses with idempotent retry |
| Denial Management | Predict denials, generate appeals citing case law, send commissioner letters |
| PMS Adapters | Integrate with practice management systems (Open Dental, CSV import/export) |
| Dashboard | React SPA for patients, claims, denials, and revenue cycle overview |

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

31 REST endpoints across 7 modules, all under the `/v1` prefix:

### Patients (`/v1/patients`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/patients` | Create a patient |
| GET | `/v1/patients` | List all patients |
| GET | `/v1/patients/{id}` | Get a patient |

### Encounters (`/v1/encounters`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/encounters/from-notes` | Parse clinical notes into structured encounter |
| POST | `/v1/encounters/from-image` | Analyze x-ray/photo via Claude Vision |
| POST | `/v1/encounters/from-voice` | Transcribe audio and parse encounter |
| GET | `/v1/encounters/{id}` | Get an encounter |

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
| POST | `/v1/denials/{id}/generate-appeal` | AI-generate appeal letter with case law |
| POST | `/v1/denials/{id}/send-commissioner-letter` | Generate and mail commissioner complaint |
| GET | `/v1/denials/{id}/commissioner-letters` | List commissioner letters for a denial |

### PMS Integration (`/v1/pms`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/pms/status` | Check PMS connection status |
| GET | `/v1/pms/patients` | List patients from PMS |
| GET | `/v1/pms/patients/{id}/encounters` | Get treatment history from PMS |
| POST | `/v1/pms/import-patient` | Import patient from PMS into Buckteeth |
| POST | `/v1/pms/import-encounter` | Import encounter from PMS into Buckteeth |

## Project Structure

```
src/buckteeth/
├── main.py              # FastAPI app entrypoint + CORS
├── config.py            # Settings (Pydantic)
├── database.py          # Async SQLAlchemy engine and session
├── tenant.py            # Multi-tenant context
├── models/              # SQLAlchemy models (patient, encounter, claim, denial, etc.)
├── api/                 # REST API routers and Pydantic schemas
│   ├── deps.py          # Shared dependencies (tenant, session)
│   ├── schemas.py       # All request/response schemas
│   ├── patients.py      # Patient CRUD
│   ├── encounters.py    # Encounter parsing (text, image, voice)
│   ├── coding.py        # AI coding engine endpoints
│   ├── claims.py        # Claim building, risk assessment, PDF
│   ├── submissions.py   # Clearinghouse submission
│   ├── denials.py       # Appeals, commissioner letters
│   └── pms.py           # PMS sync endpoints
├── ingestion/           # Clinical input parsing + image analysis + transcription
├── coding/              # AI coding engine with CDT knowledge base
├── claims/              # Claim narrative generation
├── submission/          # Clearinghouse adapter pattern + gateway
├── denials/             # Appeal generator, commissioner letters, mail service, risk scorer
├── forms/               # ADA dental claim form PDF generation (ReportLab)
├── pms/                 # PMS adapters (Mock, Open Dental, CSV)
└── knowledge/           # CDT codes, payer rules, case law repository

frontend/
├── src/
│   ├── api/             # Typed fetch client + TypeScript interfaces
│   │   ├── client.ts    # API functions for all 31 endpoints
│   │   └── types.ts     # TypeScript types matching backend schemas
│   ├── components/      # Shared UI components
│   │   ├── Layout.tsx   # Sidebar navigation shell
│   │   └── StatusBadge.tsx  # Color-coded status pill
│   ├── pages/           # Route pages
│   │   ├── Dashboard.tsx    # Summary cards + API health
│   │   ├── Patients.tsx     # Patient list + create form
│   │   ├── Claims.tsx       # Claims with status filtering + risk assessment
│   │   └── Denials.tsx      # Denials list + AI appeal generation
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

## Documentation

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
