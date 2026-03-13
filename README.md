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

- **Backend:** Python (FastAPI)
- **Frontend:** React (TypeScript)
- **Database:** PostgreSQL
- **AI:** Claude (Anthropic)
- **Auth:** AWS Cognito
- **Deployment:** Docker / AWS ECS

## Architecture

Modular monolith with clear module boundaries:

| Module | Purpose |
|--------|---------|
| Ingestion | Normalize clinical input (text, voice, images) |
| Coding Engine | AI-powered CDT/ICD-10 code selection with RAG |
| Claim Builder | Assemble claims with narratives and attachments |
| Submission Gateway | Route claims to clearinghouses |
| Denial Management | Predict denials, generate appeals, commissioner complaint letters |
| PMS Adapters | Integrate with practice management systems |
| Dashboard | Revenue cycle UI for dentists and front desk |

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- An Anthropic API key

### Setup

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

# Start the server
uvicorn buckteeth.main:app --reload
```

### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
src/buckteeth/
├── main.py              # FastAPI app entrypoint
├── config.py            # Settings
├── database.py          # DB engine and session
├── tenant.py            # Multi-tenant context
├── models/              # SQLAlchemy models
├── api/                 # REST API endpoints
├── ingestion/           # Clinical input parsing
├── coding/              # AI coding engine
├── claims/              # Claim building and narratives
├── submission/          # Clearinghouse adapters and gateway
├── denials/             # Appeals, commissioner letters, mail, risk scoring
├── forms/               # ADA claim form PDF generation
├── pms/                 # Practice management system adapters
└── knowledge/           # CDT codes, payer rules, case law
```

## Documentation

- [Design Spec](docs/superpowers/specs/2026-03-12-dental-coding-agent-design.md)
- [Phase 1 Plan: Foundation](docs/superpowers/plans/2026-03-12-phase1-foundation.md)
- [Phase 2 Plan: Claim Builder](docs/superpowers/plans/2026-03-12-phase2-claim-builder.md)
- [Phase 3 Plan: Submission Gateway](docs/superpowers/plans/2026-03-12-phase3-submission-gateway.md)
- [Phase 4 Plan: Denial Management](docs/superpowers/plans/2026-03-12-phase4-denial-management.md)
- [Phase 5 Plan: Advanced Ingestion & Risk](docs/superpowers/plans/2026-03-12-phase5-advanced-ingestion-risk.md)
- [Phase 6 Plan: PMS Adapters](docs/superpowers/plans/2026-03-13-phase6-pms-adapters.md)

## License

Proprietary. All rights reserved.
