# Phase 1: Foundation & Coding Engine MVP

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundational backend — project scaffolding, database models, CDT knowledge base, text-based clinical note ingestion, AI-powered coding engine, and API endpoints to tie it together. No frontend in Phase 1.

**Architecture:** Python FastAPI modular monolith. Each module is a Python package under `src/buckteeth/`. PostgreSQL via SQLAlchemy + Alembic. Claude API via Anthropic SDK. Tenant-scoped row-level isolation on all tables.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Anthropic SDK, PostgreSQL, pytest, Pydantic v2

---

## Chunk 1: Project Scaffolding & Database Foundation

### File Structure (Chunk 1)

```
buckteeth/
├── pyproject.toml
├── .env.example
├── .gitignore
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── buckteeth/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app entrypoint
│       ├── config.py                  # Settings via pydantic-settings
│       ├── database.py                # Engine, session factory, base model
│       ├── tenant.py                  # Tenant-scoping middleware & context
│       └── models/
│           ├── __init__.py
│           ├── base.py                # TenantScopedBase with mandatory tenant_id
│           ├── patient.py
│           ├── encounter.py
│           ├── coding.py
│           └── audit.py
├── tests/
│   ├── conftest.py                    # Fixtures: test DB, client, tenant context
│   ├── test_health.py
│   ├── test_tenant_scoping.py
│   └── models/
│       └── test_models.py
```

### Task 1: Project setup & dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "buckteeth"
version = "0.1.0"
description = "AI-powered dental insurance coding agent"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "anthropic>=0.40.0",
    "python-multipart>=0.0.12",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "testcontainers[postgres]>=4.8.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env
*.db
.coverage
htmlcov/
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 3: Create .env.example**

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/buckteeth
ANTHROPIC_API_KEY=sk-ant-xxxx
LOG_LEVEL=INFO
```

- [ ] **Step 4: Install dependencies**

Run: `cd /e/buckteeth && python -m venv .venv && source .venv/Scripts/activate && pip install -e ".[dev]"`
Expected: Successful installation with no errors

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore .env.example
git commit -m "feat: initialize project with dependencies"
```

### Task 2: Config & database setup

**Files:**
- Create: `src/buckteeth/__init__.py`
- Create: `src/buckteeth/config.py`
- Create: `src/buckteeth/database.py`

- [ ] **Step 1: Write test for config loading**

Create `tests/test_config.py`:

```python
import os
from buckteeth.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = Settings()
    assert settings.database_url == "postgresql+asyncpg://localhost/test"
    assert settings.anthropic_api_key == "sk-ant-test"
    assert settings.log_level == "INFO"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /e/buckteeth && source .venv/Scripts/activate && pytest tests/test_config.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement config.py**

Create `src/buckteeth/__init__.py` (empty file).

Create `src/buckteeth/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/buckteeth"
    anthropic_api_key: str = ""
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Write test for database session**

Create `tests/conftest.py`:

```python
import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from buckteeth.models.base import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
```

- [ ] **Step 6: Implement database.py**

Create `src/buckteeth/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from buckteeth.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 7: Commit**

```bash
git add src/buckteeth/ tests/
git commit -m "feat: add config and database session management"
```

### Task 3: Tenant-scoped base model

**Files:**
- Create: `src/buckteeth/models/__init__.py`
- Create: `src/buckteeth/models/base.py`
- Create: `src/buckteeth/tenant.py`
- Create: `tests/test_tenant_scoping.py`

- [ ] **Step 1: Write test for tenant-scoped base model**

Create `tests/test_tenant_scoping.py`:

```python
import uuid
import pytest
from sqlalchemy import select, String
from sqlalchemy.orm import Mapped, mapped_column
from buckteeth.models.base import TenantScopedBase, Base


class FakeItem(TenantScopedBase):
    __tablename__ = "fake_items"
    name: Mapped[str] = mapped_column(String(100))


@pytest.fixture(autouse=True)
async def create_table(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_tenant_scoped_model_requires_tenant_id(db_session):
    tenant_id = uuid.uuid4()
    item = FakeItem(tenant_id=tenant_id, name="test")
    db_session.add(item)
    await db_session.flush()
    assert item.id is not None
    assert item.tenant_id == tenant_id


async def test_tenant_scoped_model_has_timestamps(db_session):
    tenant_id = uuid.uuid4()
    item = FakeItem(tenant_id=tenant_id, name="test")
    db_session.add(item)
    await db_session.flush()
    assert item.created_at is not None
    assert item.updated_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tenant_scoping.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement base models**

Create `src/buckteeth/models/__init__.py` (empty file).

Create `src/buckteeth/models/base.py`:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantScopedBase(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: Update conftest for aiosqlite support**

Add `aiosqlite` to dev dependencies in pyproject.toml and reinstall. Update the conftest UUID column to work with SQLite for tests.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tenant_scoping.py -v`
Expected: PASS

- [ ] **Step 6: Implement tenant context**

Create `src/buckteeth/tenant.py`:

```python
import uuid
from contextvars import ContextVar

_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> uuid.UUID:
    tenant_id = _current_tenant_id.get()
    if tenant_id is None:
        raise RuntimeError("No tenant context set. All operations require a tenant.")
    return tenant_id


def set_current_tenant_id(tenant_id: uuid.UUID) -> None:
    _current_tenant_id.set(tenant_id)
```

- [ ] **Step 7: Commit**

```bash
git add src/buckteeth/models/ src/buckteeth/tenant.py tests/
git commit -m "feat: add tenant-scoped base model with row-level isolation"
```

### Task 4: Domain models — Patient, Encounter, Coding

**Files:**
- Create: `src/buckteeth/models/patient.py`
- Create: `src/buckteeth/models/encounter.py`
- Create: `src/buckteeth/models/coding.py`
- Create: `src/buckteeth/models/audit.py`
- Create: `tests/models/test_models.py`

- [ ] **Step 1: Write test for Patient model**

Create `tests/models/__init__.py` (empty) and `tests/models/test_models.py`:

```python
import uuid
import pytest
from sqlalchemy import select
from buckteeth.models.patient import Patient, InsurancePlan
from buckteeth.models.base import Base


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_create_patient(db_session):
    tenant = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1990-01-15",
        gender="F",
    )
    db_session.add(patient)
    await db_session.flush()
    assert patient.id is not None


async def test_patient_with_insurance(db_session):
    tenant = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1990-01-15",
        gender="F",
    )
    db_session.add(patient)
    await db_session.flush()

    plan = InsurancePlan(
        tenant_id=tenant,
        patient_id=patient.id,
        payer_name="Delta Dental",
        payer_id="DD001",
        subscriber_id="SUB123",
        group_number="GRP456",
        plan_type="primary",
    )
    db_session.add(plan)
    await db_session.flush()
    assert plan.patient_id == patient.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_models.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement Patient model**

Create `src/buckteeth/models/patient.py`:

```python
import uuid
from datetime import date
from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from buckteeth.models.base import TenantScopedBase


class Patient(TenantScopedBase):
    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[str] = mapped_column(String(10))
    gender: Mapped[str] = mapped_column(String(10))

    insurance_plans: Mapped[list["InsurancePlan"]] = relationship(back_populates="patient")


class InsurancePlan(TenantScopedBase):
    __tablename__ = "insurance_plans"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    payer_name: Mapped[str] = mapped_column(String(200))
    payer_id: Mapped[str] = mapped_column(String(50))
    subscriber_id: Mapped[str] = mapped_column(String(100))
    group_number: Mapped[str] = mapped_column(String(100))
    plan_type: Mapped[str] = mapped_column(String(20))  # primary, secondary

    patient: Mapped["Patient"] = relationship(back_populates="insurance_plans")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Implement Encounter and Coding models**

Create `src/buckteeth/models/encounter.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from buckteeth.models.base import TenantScopedBase


class ClinicalEncounter(TenantScopedBase):
    __tablename__ = "clinical_encounters"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(200))
    date_of_service: Mapped[str] = mapped_column(String(10))
    raw_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input_type: Mapped[str] = mapped_column(String(20))  # text, voice, image, structured
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, parsed, coded, error

    procedures: Mapped[list["ClinicalProcedure"]] = relationship(back_populates="encounter")


class ClinicalProcedure(TenantScopedBase):
    __tablename__ = "clinical_procedures"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clinical_encounters.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text)
    tooth_numbers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    surfaces: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)

    encounter: Mapped["ClinicalEncounter"] = relationship(back_populates="procedures")
```

Create `src/buckteeth/models/coding.py`:

```python
import uuid
from sqlalchemy import String, Text, ForeignKey, Integer, JSON, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from buckteeth.models.base import TenantScopedBase


class CodedEncounter(TenantScopedBase):
    __tablename__ = "coded_encounters"

    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clinical_encounters.id"), nullable=False, unique=True
    )
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, modified, rejected

    coded_procedures: Mapped[list["CodedProcedure"]] = relationship(back_populates="coded_encounter")


class CodedProcedure(TenantScopedBase):
    __tablename__ = "coded_procedures"

    coded_encounter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("coded_encounters.id"), nullable=False
    )
    clinical_procedure_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("clinical_procedures.id"), nullable=False
    )
    cdt_code: Mapped[str] = mapped_column(String(10))
    cdt_description: Mapped[str] = mapped_column(Text)
    tooth_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    surfaces: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quadrant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence_score: Mapped[int] = mapped_column(Integer)  # 0-100
    ai_reasoning: Mapped[str] = mapped_column(Text)
    flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    icd10_codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_cdt_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    coded_encounter: Mapped["CodedEncounter"] = relationship(back_populates="coded_procedures")
```

Create `src/buckteeth/models/audit.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from buckteeth.models.base import TenantScopedBase


class AuditLog(TenantScopedBase):
    __tablename__ = "audit_logs"

    action: Mapped[str] = mapped_column(String(50))  # ai_coding, human_override, claim_submit, etc.
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True))
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 6: Add tests for encounter and coding models**

Append to `tests/models/test_models.py`:

```python
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure


async def test_create_encounter_with_procedures(db_session):
    tenant = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant, first_name="Jane", last_name="Doe",
        date_of_birth="1990-01-15", gender="F",
    )
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant,
        patient_id=patient.id,
        provider_name="Dr. Smith",
        date_of_service="2026-03-12",
        raw_notes="MOD composite #14, recurrent decay",
        raw_input_type="text",
    )
    db_session.add(encounter)
    await db_session.flush()

    proc = ClinicalProcedure(
        tenant_id=tenant,
        encounter_id=encounter.id,
        description="MOD composite restoration",
        tooth_numbers={"teeth": [14]},
        surfaces={"surfaces": ["M", "O", "D"]},
        diagnosis="recurrent decay",
    )
    db_session.add(proc)
    await db_session.flush()
    assert proc.encounter_id == encounter.id


async def test_create_coded_encounter(db_session):
    tenant = uuid.uuid4()
    patient = Patient(
        tenant_id=tenant, first_name="Jane", last_name="Doe",
        date_of_birth="1990-01-15", gender="F",
    )
    db_session.add(patient)
    await db_session.flush()

    encounter = ClinicalEncounter(
        tenant_id=tenant, patient_id=patient.id,
        provider_name="Dr. Smith", date_of_service="2026-03-12",
        raw_notes="test", raw_input_type="text",
    )
    db_session.add(encounter)
    await db_session.flush()

    proc = ClinicalProcedure(
        tenant_id=tenant, encounter_id=encounter.id,
        description="MOD composite", diagnosis="decay",
    )
    db_session.add(proc)
    await db_session.flush()

    coded = CodedEncounter(
        tenant_id=tenant, encounter_id=encounter.id,
    )
    db_session.add(coded)
    await db_session.flush()

    coded_proc = CodedProcedure(
        tenant_id=tenant,
        coded_encounter_id=coded.id,
        clinical_procedure_id=proc.id,
        cdt_code="D2393",
        cdt_description="Resin-based composite - three surfaces, posterior",
        confidence_score=95,
        ai_reasoning="MOD composite on posterior tooth #14 maps to D2393",
    )
    db_session.add(coded_proc)
    await db_session.flush()
    assert coded_proc.cdt_code == "D2393"
```

- [ ] **Step 7: Run all model tests**

Run: `pytest tests/models/ -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/buckteeth/models/ tests/models/
git commit -m "feat: add Patient, Encounter, Coding, and Audit domain models"
```

### Task 5: FastAPI app with health endpoint

**Files:**
- Create: `src/buckteeth/main.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write test for health endpoint**

Create `tests/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from buckteeth.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL

- [ ] **Step 3: Implement main.py**

Create `src/buckteeth/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(
    title="Buckteeth",
    description="AI-powered dental insurance coding agent",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/main.py tests/test_health.py
git commit -m "feat: add FastAPI app with health endpoint"
```

### Task 6: Alembic setup

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/` (directory)

- [ ] **Step 1: Initialize alembic**

Run: `cd /e/buckteeth && source .venv/Scripts/activate && alembic init alembic`

- [ ] **Step 2: Update alembic/env.py to use async and import models**

Replace `alembic/env.py` contents:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from buckteeth.config import settings
from buckteeth.models.base import Base
from buckteeth.models import patient, encounter, coding, audit  # noqa: F401 — register models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 3: Update alembic.ini sqlalchemy.url to empty** (we load from config)

Set `sqlalchemy.url =` (empty) in alembic.ini.

- [ ] **Step 4: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: configure Alembic for async database migrations"
```

---

## Chunk 2: CDT Knowledge Base & Ingestion Module

### File Structure (Chunk 2)

```
src/buckteeth/
├── knowledge/
│   ├── __init__.py
│   ├── cdt_codes.py          # CDT code model and repository
│   ├── payer_rules.py         # Payer rule model and repository
│   └── seed_data.py           # Seed development CDT codes (no ADA-licensed content)
├── ingestion/
│   ├── __init__.py
│   ├── text_parser.py         # Claude-powered clinical note parser
│   └── schemas.py             # Pydantic schemas for parsed output
tests/
├── knowledge/
│   └── test_cdt_codes.py
├── ingestion/
│   └── test_text_parser.py
```

### Task 7: CDT code reference database

**Files:**
- Create: `src/buckteeth/knowledge/__init__.py`
- Create: `src/buckteeth/knowledge/cdt_codes.py`
- Create: `src/buckteeth/knowledge/seed_data.py`
- Create: `tests/knowledge/test_cdt_codes.py`

- [ ] **Step 1: Write test for CDT code lookup**

Create `tests/knowledge/__init__.py` (empty) and `tests/knowledge/test_cdt_codes.py`:

```python
import pytest
from buckteeth.knowledge.cdt_codes import CDTCodeRepository


@pytest.fixture
def repo():
    return CDTCodeRepository()


def test_lookup_exact_code(repo):
    result = repo.lookup("D2393")
    assert result is not None
    assert result.code == "D2393"
    assert result.category == "restorative"


def test_search_by_keyword(repo):
    results = repo.search("composite posterior")
    assert len(results) > 0
    assert any(r.code.startswith("D239") for r in results)


def test_search_by_category(repo):
    results = repo.search_by_category("preventive")
    assert len(results) > 0
    assert all(r.category == "preventive" for r in results)


def test_get_candidates_for_procedure(repo):
    candidates = repo.get_candidates("MOD composite restoration posterior tooth")
    assert len(candidates) > 0
    assert len(candidates) <= 10  # return at most 10 candidates


def test_unknown_code_returns_none(repo):
    result = repo.lookup("D9999")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_cdt_codes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CDT code repository**

Create `src/buckteeth/knowledge/__init__.py` (empty).

Create `src/buckteeth/knowledge/cdt_codes.py`:

```python
from dataclasses import dataclass


@dataclass
class CDTCode:
    code: str
    description: str
    category: str
    subcategory: str
    common_scenarios: list[str]
    confused_with: list[str]
    bundling_notes: str
    frequency_notes: str
    narrative_required: bool
    common_denial_reasons: list[str]


class CDTCodeRepository:
    """In-memory CDT code reference. Loaded from seed data or imported JSON/CSV."""

    def __init__(self, codes: list[CDTCode] | None = None):
        from buckteeth.knowledge.seed_data import SEED_CDT_CODES

        self._codes = {c.code: c for c in (codes or SEED_CDT_CODES)}
        self._by_category: dict[str, list[CDTCode]] = {}
        for code in self._codes.values():
            self._by_category.setdefault(code.category, []).append(code)

    def lookup(self, code: str) -> CDTCode | None:
        return self._codes.get(code)

    def search(self, query: str) -> list[CDTCode]:
        query_lower = query.lower()
        terms = query_lower.split()
        results = []
        for code in self._codes.values():
            searchable = f"{code.description} {code.category} {code.subcategory} {' '.join(code.common_scenarios)}".lower()
            if all(t in searchable for t in terms):
                results.append(code)
        return results[:10]

    def search_by_category(self, category: str) -> list[CDTCode]:
        return self._by_category.get(category, [])

    def get_candidates(self, procedure_description: str) -> list[CDTCode]:
        """Return up to 10 candidate codes for a procedure description."""
        desc_lower = procedure_description.lower()
        scored: list[tuple[int, CDTCode]] = []
        for code in self._codes.values():
            searchable = f"{code.description} {' '.join(code.common_scenarios)}".lower()
            score = sum(1 for term in desc_lower.split() if term in searchable)
            if score > 0:
                scored.append((score, code))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [code for _, code in scored[:10]]
```

- [ ] **Step 4: Create seed data**

Create `src/buckteeth/knowledge/seed_data.py`:

```python
"""
Development seed data for CDT codes. Uses abbreviated descriptions only —
official ADA descriptors require a license. This is sufficient for development
and testing.
"""
from buckteeth.knowledge.cdt_codes import CDTCode

SEED_CDT_CODES = [
    # Diagnostic
    CDTCode("D0120", "Periodic oral evaluation", "diagnostic", "evaluation",
            ["routine checkup", "recall exam"], ["D0150"], "", "2x per year most plans", False, []),
    CDTCode("D0140", "Limited oral evaluation - problem focused", "diagnostic", "evaluation",
            ["emergency exam", "toothache visit"], ["D0120"], "", "", False, []),
    CDTCode("D0150", "Comprehensive oral evaluation - new or established patient", "diagnostic", "evaluation",
            ["new patient exam", "comprehensive exam"], ["D0120", "D0180"], "", "1x per 3 years", False, []),
    CDTCode("D0180", "Comprehensive periodontal evaluation", "diagnostic", "evaluation",
            ["perio exam", "periodontal evaluation"], ["D0150"], "", "1x per 3 years", False, []),
    CDTCode("D0210", "Intraoral - complete series of radiographic images", "diagnostic", "radiograph",
            ["full mouth xrays", "FMX", "complete series"], ["D0330"], "", "1x per 3-5 years", False, []),
    CDTCode("D0220", "Intraoral - periapical first radiographic image", "diagnostic", "radiograph",
            ["PA xray", "periapical"], ["D0230"], "", "", False, []),
    CDTCode("D0230", "Intraoral - periapical each additional radiographic image", "diagnostic", "radiograph",
            ["additional PA"], ["D0220"], "Requires D0220 first", "", False, []),
    CDTCode("D0272", "Bitewings - two radiographic images", "diagnostic", "radiograph",
            ["2 BWX", "two bitewings"], ["D0274"], "", "1-2x per year", False, []),
    CDTCode("D0274", "Bitewings - four radiographic images", "diagnostic", "radiograph",
            ["4 BWX", "four bitewings"], ["D0272"], "", "1-2x per year", False, []),
    CDTCode("D0330", "Panoramic radiographic image", "diagnostic", "radiograph",
            ["pano", "panoramic", "panorex"], ["D0210"], "", "1x per 3-5 years", False, []),

    # Preventive
    CDTCode("D1110", "Prophylaxis - adult", "preventive", "cleaning",
            ["adult prophy", "adult cleaning", "teeth cleaning"], ["D4341", "D4342"],
            "Cannot bill with D4341/D4342 same day", "2x per year", False,
            ["frequency exceeded", "downcode to D1110 from SRP"]),
    CDTCode("D1120", "Prophylaxis - child", "preventive", "cleaning",
            ["child prophy", "child cleaning"], ["D1110"], "", "2x per year", False, []),
    CDTCode("D1206", "Topical application of fluoride varnish", "preventive", "fluoride",
            ["fluoride varnish", "fluoride treatment"], ["D1208"],
            "Cannot bill with D1208 same visit", "2x per year", False, []),
    CDTCode("D1351", "Sealant - per tooth", "preventive", "sealant",
            ["pit and fissure sealant", "sealant"], [], "", "1x per tooth, age limits apply", False,
            ["age limitation", "tooth already sealed"]),

    # Restorative
    CDTCode("D2140", "Amalgam - one surface, primary or permanent", "restorative", "amalgam",
            ["one surface amalgam", "single surface filling"], ["D2330"], "", "", False, []),
    CDTCode("D2150", "Amalgam - two surfaces, primary or permanent", "restorative", "amalgam",
            ["two surface amalgam", "MO amalgam", "DO amalgam"], ["D2331"], "", "", False, []),
    CDTCode("D2160", "Amalgam - three surfaces, primary or permanent", "restorative", "amalgam",
            ["three surface amalgam", "MOD amalgam"], ["D2332"], "", "", False, []),
    CDTCode("D2330", "Resin-based composite - one surface, anterior", "restorative", "composite",
            ["one surface composite anterior", "anterior filling"], ["D2391"], "", "", False, []),
    CDTCode("D2331", "Resin-based composite - two surfaces, anterior", "restorative", "composite",
            ["two surface composite anterior"], ["D2392"], "", "", False, []),
    CDTCode("D2332", "Resin-based composite - three surfaces, anterior", "restorative", "composite",
            ["three surface composite anterior"], ["D2393"], "", "", False, []),
    CDTCode("D2391", "Resin-based composite - one surface, posterior", "restorative", "composite",
            ["one surface composite posterior", "posterior filling"], ["D2140"],
            "", "", False, ["downcode to amalgam"]),
    CDTCode("D2392", "Resin-based composite - two surfaces, posterior", "restorative", "composite",
            ["two surface composite posterior", "MO composite", "DO composite"], ["D2150"],
            "", "", False, ["downcode to amalgam"]),
    CDTCode("D2393", "Resin-based composite - three surfaces, posterior", "restorative", "composite",
            ["three surface composite posterior", "MOD composite"], ["D2160"],
            "", "", False, ["downcode to amalgam"]),
    CDTCode("D2394", "Resin-based composite - four or more surfaces, posterior", "restorative", "composite",
            ["four surface composite posterior", "MODL composite"], ["D2161"],
            "", "", False, ["downcode to amalgam"]),
    CDTCode("D2740", "Crown - porcelain/ceramic substrate", "restorative", "crown",
            ["porcelain crown", "ceramic crown", "all ceramic crown", "emax crown"], ["D2750"],
            "Cannot bill with D2950 on same day by some payers", "1x per 5-10 years per tooth", True,
            ["frequency limitation", "missing narrative"]),
    CDTCode("D2750", "Crown - porcelain fused to high noble metal", "restorative", "crown",
            ["PFM crown", "porcelain fused to metal"], ["D2740"],
            "", "1x per 5-10 years per tooth", True, ["frequency limitation"]),
    CDTCode("D2950", "Core buildup, including any pins when required", "restorative", "crown",
            ["core buildup", "buildup"], [],
            "Often bundled with crown by payers", "", True,
            ["bundled with crown", "missing narrative"]),

    # Endodontics
    CDTCode("D3310", "Endodontic therapy, anterior tooth", "endodontics", "root_canal",
            ["anterior root canal", "front tooth root canal"], ["D3320"],
            "", "", True, ["missing PA xray"]),
    CDTCode("D3320", "Endodontic therapy, premolar tooth", "endodontics", "root_canal",
            ["premolar root canal", "bicuspid root canal"], ["D3310", "D3330"],
            "", "", True, []),
    CDTCode("D3330", "Endodontic therapy, molar tooth", "endodontics", "root_canal",
            ["molar root canal"], ["D3320"],
            "", "", True, []),

    # Periodontics
    CDTCode("D4341", "Periodontal scaling and root planing - four or more teeth per quadrant", "periodontics", "srp",
            ["SRP", "scaling and root planing", "deep cleaning"], ["D1110"],
            "Cannot bill with D1110 same day", "1x per quadrant per 2 years", True,
            ["missing perio charting", "insufficient pocket depths"]),
    CDTCode("D4342", "Periodontal scaling and root planing - one to three teeth per quadrant", "periodontics", "srp",
            ["limited SRP", "localized scaling"], ["D4341"],
            "", "1x per quadrant per 2 years", True, []),
    CDTCode("D4910", "Periodontal maintenance", "periodontics", "maintenance",
            ["perio maintenance", "periodontal recall"], ["D1110"],
            "Replaces D1110 after active perio therapy", "3-4x per year", False,
            ["no prior SRP on record"]),

    # Oral Surgery
    CDTCode("D7140", "Extraction, erupted tooth or exposed root", "oral_surgery", "extraction",
            ["simple extraction", "routine extraction"], ["D7210"],
            "", "", False, []),
    CDTCode("D7210", "Extraction, erupted tooth requiring removal of bone and/or sectioning of tooth", "oral_surgery", "extraction",
            ["surgical extraction"], ["D7140", "D7220"],
            "", "", True, ["missing narrative", "missing xray"]),
    CDTCode("D7220", "Removal of impacted tooth - soft tissue", "oral_surgery", "extraction",
            ["soft tissue impaction", "impacted wisdom tooth"], ["D7230", "D7240"],
            "", "", True, []),
    CDTCode("D7230", "Removal of impacted tooth - partially bony", "oral_surgery", "extraction",
            ["partial bony impaction"], ["D7220", "D7240"],
            "", "", True, []),
    CDTCode("D7240", "Removal of impacted tooth - completely bony", "oral_surgery", "extraction",
            ["full bony impaction", "complete bony impaction"], ["D7230"],
            "", "", True, []),

    # Prosthodontics
    CDTCode("D5110", "Complete denture - maxillary", "prosthodontics", "denture",
            ["upper denture", "maxillary complete denture"], ["D5130"],
            "", "1x per 5-10 years", True, []),
    CDTCode("D5120", "Complete denture - mandibular", "prosthodontics", "denture",
            ["lower denture", "mandibular complete denture"], ["D5140"],
            "", "1x per 5-10 years", True, []),

    # Adjunctive
    CDTCode("D9110", "Palliative treatment of dental pain", "adjunctive", "palliative",
            ["emergency pain treatment", "palliative care"], [],
            "", "", False, []),
    CDTCode("D9230", "Inhalation of nitrous oxide", "adjunctive", "anesthesia",
            ["nitrous oxide", "laughing gas"], [],
            "", "", False, ["not covered by plan"]),
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/knowledge/test_cdt_codes.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/knowledge/ tests/knowledge/
git commit -m "feat: add CDT code reference database with seed data"
```

### Task 8: Payer rules reference

**Files:**
- Create: `src/buckteeth/knowledge/payer_rules.py`
- Create: `tests/knowledge/test_payer_rules.py`

- [ ] **Step 1: Write test for payer rule lookup**

Create `tests/knowledge/test_payer_rules.py`:

```python
from buckteeth.knowledge.payer_rules import PayerRuleRepository


def test_get_frequency_limit():
    repo = PayerRuleRepository()
    limit = repo.get_frequency_limit("delta_dental", "D1110")
    assert limit is not None
    assert limit.max_per_period > 0


def test_check_frequency_ok():
    repo = PayerRuleRepository()
    result = repo.check_frequency("delta_dental", "D1110", months_since_last=7)
    assert result.allowed is True


def test_check_frequency_too_soon():
    repo = PayerRuleRepository()
    result = repo.check_frequency("delta_dental", "D1110", months_since_last=3)
    assert result.allowed is False
    assert "frequency" in result.reason.lower()


def test_get_bundling_rules():
    repo = PayerRuleRepository()
    rules = repo.get_bundling_rules("D2950")
    assert len(rules) > 0


def test_unknown_payer_returns_defaults():
    repo = PayerRuleRepository()
    limit = repo.get_frequency_limit("unknown_payer", "D1110")
    assert limit is not None  # falls back to default rules
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/knowledge/test_payer_rules.py -v`
Expected: FAIL

- [ ] **Step 3: Implement payer rules repository**

Create `src/buckteeth/knowledge/payer_rules.py`:

```python
from dataclasses import dataclass


@dataclass
class FrequencyLimit:
    code: str
    max_per_period: int
    period_months: int
    age_min: int | None = None
    age_max: int | None = None
    notes: str = ""


@dataclass
class FrequencyCheckResult:
    allowed: bool
    reason: str


@dataclass
class BundlingRule:
    code: str
    bundled_with: str
    rule: str  # "cannot_bill_together", "requires_prior", "often_denied_together"
    notes: str = ""


# Default frequency rules (conservative, used when payer-specific rules unknown)
_DEFAULT_FREQUENCY: dict[str, FrequencyLimit] = {
    "D0120": FrequencyLimit("D0120", 2, 12),
    "D0150": FrequencyLimit("D0150", 1, 36),
    "D0210": FrequencyLimit("D0210", 1, 60),
    "D0272": FrequencyLimit("D0272", 2, 12),
    "D0274": FrequencyLimit("D0274", 2, 12),
    "D0330": FrequencyLimit("D0330", 1, 60),
    "D1110": FrequencyLimit("D1110", 2, 12),
    "D1120": FrequencyLimit("D1120", 2, 12),
    "D1206": FrequencyLimit("D1206", 2, 12),
    "D1351": FrequencyLimit("D1351", 1, 36, age_max=16),
    "D2740": FrequencyLimit("D2740", 1, 60),
    "D2750": FrequencyLimit("D2750", 1, 60),
    "D4341": FrequencyLimit("D4341", 1, 24),
    "D4342": FrequencyLimit("D4342", 1, 24),
}

# Payer-specific overrides
_PAYER_FREQUENCY: dict[str, dict[str, FrequencyLimit]] = {
    "delta_dental": {
        "D1110": FrequencyLimit("D1110", 2, 12, notes="Every 6 months"),
        "D0274": FrequencyLimit("D0274", 1, 12, notes="Once per year"),
        "D2740": FrequencyLimit("D2740", 1, 60, notes="Once per 5 years per tooth"),
    },
    "metlife": {
        "D1110": FrequencyLimit("D1110", 2, 12),
        "D0274": FrequencyLimit("D0274", 2, 12),
    },
}

_BUNDLING_RULES: list[BundlingRule] = [
    BundlingRule("D2950", "D2740", "often_denied_together", "Core buildup often bundled with crown"),
    BundlingRule("D2950", "D2750", "often_denied_together", "Core buildup often bundled with crown"),
    BundlingRule("D1110", "D4341", "cannot_bill_together", "Cannot bill prophy and SRP same day"),
    BundlingRule("D1110", "D4342", "cannot_bill_together", "Cannot bill prophy and SRP same day"),
    BundlingRule("D1206", "D1208", "cannot_bill_together", "Cannot bill two fluoride types same visit"),
    BundlingRule("D0220", "D0230", "requires_prior", "D0230 requires D0220 first"),
]


class PayerRuleRepository:

    def get_frequency_limit(self, payer_id: str, cdt_code: str) -> FrequencyLimit | None:
        payer_rules = _PAYER_FREQUENCY.get(payer_id, {})
        if cdt_code in payer_rules:
            return payer_rules[cdt_code]
        return _DEFAULT_FREQUENCY.get(cdt_code)

    def check_frequency(
        self, payer_id: str, cdt_code: str, months_since_last: int | None = None
    ) -> FrequencyCheckResult:
        limit = self.get_frequency_limit(payer_id, cdt_code)
        if limit is None:
            return FrequencyCheckResult(allowed=True, reason="No frequency limit on record")
        if months_since_last is None:
            return FrequencyCheckResult(allowed=True, reason="No prior history")
        interval = limit.period_months // limit.max_per_period
        if months_since_last < interval:
            return FrequencyCheckResult(
                allowed=False,
                reason=f"Frequency limit: {limit.max_per_period}x per {limit.period_months} months. "
                       f"Last performed {months_since_last} months ago, need {interval} months between.",
            )
        return FrequencyCheckResult(allowed=True, reason="Within frequency limits")

    def get_bundling_rules(self, cdt_code: str) -> list[BundlingRule]:
        return [r for r in _BUNDLING_RULES if r.code == cdt_code or r.bundled_with == cdt_code]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/knowledge/test_payer_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/knowledge/payer_rules.py tests/knowledge/test_payer_rules.py
git commit -m "feat: add payer rules repository with frequency and bundling checks"
```

### Task 9: Clinical note text parser (Claude-powered)

**Files:**
- Create: `src/buckteeth/ingestion/__init__.py`
- Create: `src/buckteeth/ingestion/schemas.py`
- Create: `src/buckteeth/ingestion/text_parser.py`
- Create: `tests/ingestion/__init__.py`
- Create: `tests/ingestion/test_text_parser.py`

- [ ] **Step 1: Define Pydantic schemas for parsed output**

Create `src/buckteeth/ingestion/__init__.py` (empty).

Create `src/buckteeth/ingestion/schemas.py`:

```python
from pydantic import BaseModel


class ParsedProcedure(BaseModel):
    description: str
    tooth_numbers: list[int] | None = None
    surfaces: list[str] | None = None
    quadrant: str | None = None
    diagnosis: str | None = None


class ParsedEncounter(BaseModel):
    procedures: list[ParsedProcedure]
    notes: str | None = None
```

- [ ] **Step 2: Write test for text parser**

Create `tests/ingestion/__init__.py` (empty) and `tests/ingestion/test_text_parser.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure


@pytest.fixture
def parser():
    return ClinicalNoteParser(api_key="test-key")


def _mock_claude_response(parsed: ParsedEncounter) -> MagicMock:
    """Create a mock Claude response with structured content."""
    mock_block = MagicMock()
    mock_block.text = parsed.model_dump_json()
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_parse_simple_note(parser):
    expected = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="MOD composite restoration",
                tooth_numbers=[14],
                surfaces=["M", "O", "D"],
                diagnosis="recurrent decay",
            )
        ]
    )
    with patch.object(
        parser._client.messages, "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("MOD composite #14, recurrent decay")
        assert len(result.procedures) == 1
        assert result.procedures[0].tooth_numbers == [14]
        assert result.procedures[0].surfaces == ["M", "O", "D"]


async def test_parse_multiple_procedures(parser):
    expected = ParsedEncounter(
        procedures=[
            ParsedProcedure(description="Prophylaxis adult", tooth_numbers=None),
            ParsedProcedure(description="Four bitewing radiographs", tooth_numbers=None),
            ParsedProcedure(description="Periodic oral evaluation", tooth_numbers=None),
        ]
    )
    with patch.object(
        parser._client.messages, "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("Adult prophy, 4BWX, periodic eval")
        assert len(result.procedures) == 3


async def test_parse_returns_empty_on_no_procedures(parser):
    expected = ParsedEncounter(procedures=[])
    with patch.object(
        parser._client.messages, "create",
        new_callable=AsyncMock,
        return_value=_mock_claude_response(expected),
    ):
        result = await parser.parse("Patient presented for consultation only")
        assert len(result.procedures) == 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/ingestion/test_text_parser.py -v`
Expected: FAIL

- [ ] **Step 4: Implement text parser**

Create `src/buckteeth/ingestion/text_parser.py`:

```python
import json
import anthropic
from buckteeth.ingestion.schemas import ParsedEncounter

SYSTEM_PROMPT = """You are a dental clinical note parser. Extract structured procedure data from dental clinical notes.

For each procedure mentioned, extract:
- description: What was done (e.g., "MOD composite restoration")
- tooth_numbers: List of tooth numbers using universal numbering (1-32), or null if not tooth-specific
- surfaces: List of surfaces (M=mesial, O=occlusal, D=distal, B=buccal, L=lingual, F=facial, I=incisal), or null
- quadrant: UR, UL, LR, LL, or null
- diagnosis: The condition being treated, or null

Common abbreviations:
- MOD, DO, MO, etc. = surface combinations
- comp = composite
- amal = amalgam
- prophy = prophylaxis (cleaning)
- BWX = bitewing x-rays
- FMX = full mouth x-rays
- PA = periapical
- SRP = scaling and root planing
- RCT = root canal therapy
- ext = extraction
- # followed by number = tooth number

Return a JSON object with a "procedures" array. If no procedures are found, return {"procedures": []}.
"""


class ClinicalNoteParser:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def parse(self, clinical_notes: str) -> ParsedEncounter:
        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Parse the following dental clinical notes into structured procedure data:\n\n{clinical_notes}",
                }
            ],
        )
        text = response.content[0].text
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())
        return ParsedEncounter.model_validate(data)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/ingestion/test_text_parser.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/ingestion/ tests/ingestion/
git commit -m "feat: add Claude-powered clinical note text parser"
```

---

## Chunk 3: Coding Engine

### File Structure (Chunk 3)

```
src/buckteeth/
├── coding/
│   ├── __init__.py
│   ├── engine.py              # Main coding engine orchestrator
│   ├── cdt_selector.py        # Claude-powered CDT code selection
│   ├── validators.py          # Frequency, bundling, confidence checks
│   └── schemas.py             # Pydantic schemas for coding output
tests/
├── coding/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_cdt_selector.py
│   └── test_validators.py
```

### Task 10: Coding output schemas

**Files:**
- Create: `src/buckteeth/coding/__init__.py`
- Create: `src/buckteeth/coding/schemas.py`

- [ ] **Step 1: Create coding schemas**

Create `src/buckteeth/coding/__init__.py` (empty).

Create `src/buckteeth/coding/schemas.py`:

```python
from pydantic import BaseModel


class CodeSuggestion(BaseModel):
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    confidence_score: int  # 0-100
    ai_reasoning: str
    flags: list[str] = []
    icd10_codes: list[str] = []


class CodingResult(BaseModel):
    suggestions: list[CodeSuggestion]
    encounter_notes: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add src/buckteeth/coding/
git commit -m "feat: add coding output schemas"
```

### Task 11: Validators (frequency, bundling)

**Files:**
- Create: `src/buckteeth/coding/validators.py`
- Create: `tests/coding/__init__.py`
- Create: `tests/coding/test_validators.py`

- [ ] **Step 1: Write test for validators**

Create `tests/coding/__init__.py` (empty) and `tests/coding/test_validators.py`:

```python
from buckteeth.coding.validators import CodingValidator
from buckteeth.coding.schemas import CodeSuggestion


def test_flag_frequency_violation():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D1110", cdt_description="Prophylaxis - adult",
        confidence_score=95, ai_reasoning="routine cleaning",
    )
    result = validator.validate(suggestion, payer_id="delta_dental", months_since_last={"D1110": 3})
    assert "frequency_concern" in result.flags


def test_no_flag_when_frequency_ok():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D1110", cdt_description="Prophylaxis - adult",
        confidence_score=95, ai_reasoning="routine cleaning",
    )
    result = validator.validate(suggestion, payer_id="delta_dental", months_since_last={"D1110": 7})
    assert "frequency_concern" not in result.flags


def test_flag_bundling_risk():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D2950", cdt_description="Core buildup",
        confidence_score=90, ai_reasoning="buildup needed",
    )
    result = validator.validate(
        suggestion, payer_id="delta_dental",
        other_codes_in_encounter=["D2740"],
    )
    assert "bundling_risk" in result.flags


def test_flag_low_confidence():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D7210", cdt_description="Surgical extraction",
        confidence_score=65, ai_reasoning="might need surgical approach",
    )
    result = validator.validate(suggestion, payer_id="delta_dental")
    assert "low_confidence" in result.flags


def test_flag_narrative_required():
    validator = CodingValidator()
    suggestion = CodeSuggestion(
        cdt_code="D4341", cdt_description="SRP - 4+ teeth per quadrant",
        confidence_score=92, ai_reasoning="perio therapy",
    )
    result = validator.validate(suggestion, payer_id="delta_dental")
    assert "needs_narrative" in result.flags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/coding/test_validators.py -v`
Expected: FAIL

- [ ] **Step 3: Implement validators**

Create `src/buckteeth/coding/validators.py`:

```python
from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.knowledge.cdt_codes import CDTCodeRepository
from buckteeth.knowledge.payer_rules import PayerRuleRepository


class CodingValidator:

    def __init__(self):
        self._cdt_repo = CDTCodeRepository()
        self._payer_repo = PayerRuleRepository()

    def validate(
        self,
        suggestion: CodeSuggestion,
        payer_id: str = "default",
        months_since_last: dict[str, int] | None = None,
        other_codes_in_encounter: list[str] | None = None,
    ) -> CodeSuggestion:
        flags = list(suggestion.flags)

        # Check frequency
        if months_since_last and suggestion.cdt_code in months_since_last:
            freq_result = self._payer_repo.check_frequency(
                payer_id, suggestion.cdt_code, months_since_last[suggestion.cdt_code]
            )
            if not freq_result.allowed:
                flags.append("frequency_concern")

        # Check bundling
        if other_codes_in_encounter:
            bundling_rules = self._payer_repo.get_bundling_rules(suggestion.cdt_code)
            for rule in bundling_rules:
                paired = rule.bundled_with if rule.code == suggestion.cdt_code else rule.code
                if paired in other_codes_in_encounter:
                    flags.append("bundling_risk")
                    break

        # Check confidence
        if suggestion.confidence_score < 75:
            flags.append("low_confidence")

        # Check if narrative required
        cdt_info = self._cdt_repo.lookup(suggestion.cdt_code)
        if cdt_info and cdt_info.narrative_required:
            flags.append("needs_narrative")

        return suggestion.model_copy(update={"flags": flags})
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/coding/test_validators.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/coding/validators.py tests/coding/test_validators.py
git commit -m "feat: add coding validators for frequency, bundling, and confidence"
```

### Task 12: CDT code selector (Claude-powered)

**Files:**
- Create: `src/buckteeth/coding/cdt_selector.py`
- Create: `tests/coding/test_cdt_selector.py`

- [ ] **Step 1: Write test for CDT selector**

Create `tests/coding/test_cdt_selector.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from buckteeth.coding.cdt_selector import CDTCodeSelector
from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.ingestion.schemas import ParsedProcedure


@pytest.fixture
def selector():
    return CDTCodeSelector(api_key="test-key")


def _mock_claude_response(suggestions: list[dict]) -> MagicMock:
    import json
    mock_block = MagicMock()
    mock_block.text = json.dumps({"suggestions": suggestions})
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


async def test_select_code_for_composite(selector):
    procedure = ParsedProcedure(
        description="MOD composite restoration",
        tooth_numbers=[14],
        surfaces=["M", "O", "D"],
        diagnosis="recurrent decay",
    )
    mock_response = _mock_claude_response([{
        "cdt_code": "D2393",
        "cdt_description": "Resin-based composite - three surfaces, posterior",
        "tooth_number": "14",
        "surfaces": "MOD",
        "confidence_score": 97,
        "ai_reasoning": "Three-surface (MOD) composite on posterior tooth #14",
    }])
    with patch.object(
        selector._client.messages, "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        results = await selector.select_codes(procedure)
        assert len(results) == 1
        assert results[0].cdt_code == "D2393"
        assert results[0].confidence_score == 97


async def test_select_code_for_prophy(selector):
    procedure = ParsedProcedure(description="Adult prophylaxis")
    mock_response = _mock_claude_response([{
        "cdt_code": "D1110",
        "cdt_description": "Prophylaxis - adult",
        "confidence_score": 99,
        "ai_reasoning": "Standard adult prophylaxis",
    }])
    with patch.object(
        selector._client.messages, "create",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        results = await selector.select_codes(procedure)
        assert len(results) == 1
        assert results[0].cdt_code == "D1110"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/coding/test_cdt_selector.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CDT code selector**

Create `src/buckteeth/coding/cdt_selector.py`:

```python
import json
import anthropic
from buckteeth.coding.schemas import CodeSuggestion
from buckteeth.ingestion.schemas import ParsedProcedure
from buckteeth.knowledge.cdt_codes import CDTCodeRepository

SYSTEM_PROMPT = """You are a dental insurance coding expert. Given a clinical procedure and a list of candidate CDT codes, select the most appropriate code(s).

For each procedure, return:
- cdt_code: The CDT code
- cdt_description: Description of the code
- tooth_number: Tooth number if applicable, or null
- surfaces: Surface string (e.g., "MOD") if applicable, or null
- quadrant: Quadrant if applicable, or null
- confidence_score: 0-100 how confident you are in this code selection
- ai_reasoning: Brief explanation of why this code was selected
- icd10_codes: List of ICD-10 codes if medical cross-coding applies, or []

Return JSON with a "suggestions" array. One suggestion per procedure, unless the procedure maps to multiple codes (e.g., a procedure that requires a diagnostic code AND a treatment code).

Key coding rules:
- Composite restorations: count surfaces (1=D2391, 2=D2392, 3=D2393, 4+=D2394 for posterior; D2330-D2332 for anterior)
- Tooth numbers 1-16 are upper, 17-32 are lower
- Teeth 1-5, 12-16 are posterior upper; 6-11 are anterior upper
- Teeth 17-21, 28-32 are posterior lower; 22-27 are anterior lower
"""


class CDTCodeSelector:

    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._cdt_repo = CDTCodeRepository()

    async def select_codes(self, procedure: ParsedProcedure) -> list[CodeSuggestion]:
        candidates = self._cdt_repo.get_candidates(procedure.description)
        candidate_text = "\n".join(
            f"- {c.code}: {c.description} (category: {c.category})"
            for c in candidates
        )

        procedure_text = f"Procedure: {procedure.description}"
        if procedure.tooth_numbers:
            procedure_text += f"\nTooth numbers: {procedure.tooth_numbers}"
        if procedure.surfaces:
            procedure_text += f"\nSurfaces: {procedure.surfaces}"
        if procedure.quadrant:
            procedure_text += f"\nQuadrant: {procedure.quadrant}"
        if procedure.diagnosis:
            procedure_text += f"\nDiagnosis: {procedure.diagnosis}"

        response = await self._client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"{procedure_text}\n\nCandidate CDT codes:\n{candidate_text}",
                }
            ],
        )

        text = response.content[0].text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        data = json.loads(text.strip())

        return [CodeSuggestion.model_validate(s) for s in data["suggestions"]]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/coding/test_cdt_selector.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/buckteeth/coding/cdt_selector.py tests/coding/test_cdt_selector.py
git commit -m "feat: add Claude-powered CDT code selector with RAG"
```

### Task 13: Coding engine orchestrator

**Files:**
- Create: `src/buckteeth/coding/engine.py`
- Create: `tests/coding/test_engine.py`

- [ ] **Step 1: Write test for coding engine**

Create `tests/coding/test_engine.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from buckteeth.coding.engine import CodingEngine
from buckteeth.coding.schemas import CodeSuggestion, CodingResult
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure


@pytest.fixture
def engine():
    return CodingEngine(api_key="test-key")


async def test_code_encounter_end_to_end(engine):
    encounter = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="MOD composite restoration",
                tooth_numbers=[14],
                surfaces=["M", "O", "D"],
                diagnosis="recurrent decay",
            ),
            ParsedProcedure(description="Adult prophylaxis"),
        ]
    )
    mock_suggestions_1 = [CodeSuggestion(
        cdt_code="D2393",
        cdt_description="Resin-based composite - three surfaces, posterior",
        tooth_number="14", surfaces="MOD",
        confidence_score=97,
        ai_reasoning="MOD composite on posterior tooth #14",
    )]
    mock_suggestions_2 = [CodeSuggestion(
        cdt_code="D1110",
        cdt_description="Prophylaxis - adult",
        confidence_score=99,
        ai_reasoning="Standard adult prophylaxis",
    )]

    with patch.object(
        engine._selector, "select_codes",
        new_callable=AsyncMock,
        side_effect=[mock_suggestions_1, mock_suggestions_2],
    ):
        result = await engine.code_encounter(encounter, payer_id="delta_dental")
        assert len(result.suggestions) == 2
        codes = [s.cdt_code for s in result.suggestions]
        assert "D2393" in codes
        assert "D1110" in codes


async def test_code_encounter_adds_validation_flags(engine):
    encounter = ParsedEncounter(
        procedures=[
            ParsedProcedure(description="SRP four teeth upper right quadrant"),
        ]
    )
    mock_suggestions = [CodeSuggestion(
        cdt_code="D4341",
        cdt_description="SRP - four or more teeth per quadrant",
        quadrant="UR", confidence_score=92,
        ai_reasoning="SRP on UR quadrant",
    )]
    with patch.object(
        engine._selector, "select_codes",
        new_callable=AsyncMock,
        return_value=mock_suggestions,
    ):
        result = await engine.code_encounter(encounter, payer_id="delta_dental")
        assert "needs_narrative" in result.suggestions[0].flags
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/coding/test_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement coding engine**

Create `src/buckteeth/coding/engine.py`:

```python
from buckteeth.coding.cdt_selector import CDTCodeSelector
from buckteeth.coding.validators import CodingValidator
from buckteeth.coding.schemas import CodingResult, CodeSuggestion
from buckteeth.ingestion.schemas import ParsedEncounter


class CodingEngine:

    def __init__(self, api_key: str):
        self._selector = CDTCodeSelector(api_key=api_key)
        self._validator = CodingValidator()

    async def code_encounter(
        self,
        encounter: ParsedEncounter,
        payer_id: str = "default",
        months_since_last: dict[str, int] | None = None,
    ) -> CodingResult:
        all_suggestions: list[CodeSuggestion] = []

        # Select codes for each procedure
        for procedure in encounter.procedures:
            suggestions = await self._selector.select_codes(procedure)
            all_suggestions.extend(suggestions)

        # Collect all codes for bundling checks
        all_codes = [s.cdt_code for s in all_suggestions]

        # Validate each suggestion
        validated: list[CodeSuggestion] = []
        for suggestion in all_suggestions:
            other_codes = [c for c in all_codes if c != suggestion.cdt_code]
            result = self._validator.validate(
                suggestion,
                payer_id=payer_id,
                months_since_last=months_since_last,
                other_codes_in_encounter=other_codes,
            )
            validated.append(result)

        return CodingResult(suggestions=validated)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/coding/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/coding/engine.py tests/coding/test_engine.py
git commit -m "feat: add coding engine orchestrator with validation pipeline"
```

---

## Chunk 4: API Endpoints

### File Structure (Chunk 4)

```
src/buckteeth/
├── api/
│   ├── __init__.py
│   ├── deps.py                # Shared dependencies (DB session, tenant, auth)
│   ├── patients.py            # Patient CRUD endpoints
│   ├── encounters.py          # Encounter + ingestion endpoints
│   ├── coding.py              # Coding endpoints
│   └── schemas.py             # API request/response schemas
tests/
├── api/
│   ├── __init__.py
│   ├── test_patients.py
│   ├── test_encounters.py
│   └── test_coding.py
```

### Task 14: API dependencies and schemas

**Files:**
- Create: `src/buckteeth/api/__init__.py`
- Create: `src/buckteeth/api/deps.py`
- Create: `src/buckteeth/api/schemas.py`

- [ ] **Step 1: Create API schemas**

Create `src/buckteeth/api/__init__.py` (empty).

Create `src/buckteeth/api/schemas.py`:

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


# Error response
class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


# Patient
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str


class PatientResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InsurancePlanCreate(BaseModel):
    payer_name: str
    payer_id: str
    subscriber_id: str
    group_number: str
    plan_type: str  # primary, secondary


class InsurancePlanResponse(BaseModel):
    id: uuid.UUID
    payer_name: str
    payer_id: str
    subscriber_id: str
    group_number: str
    plan_type: str

    model_config = {"from_attributes": True}


# Encounter
class EncounterFromNotesRequest(BaseModel):
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
    notes: str


class ClinicalProcedureResponse(BaseModel):
    id: uuid.UUID
    description: str
    tooth_numbers: dict | None = None
    surfaces: dict | None = None
    quadrant: str | None = None
    diagnosis: str | None = None

    model_config = {"from_attributes": True}


class EncounterResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_name: str
    date_of_service: str
    raw_notes: str | None
    raw_input_type: str
    status: str
    procedures: list[ClinicalProcedureResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# Coding
class CodeEncounterRequest(BaseModel):
    payer_id: str = "default"


class CodedProcedureResponse(BaseModel):
    id: uuid.UUID
    cdt_code: str
    cdt_description: str
    tooth_number: str | None = None
    surfaces: str | None = None
    quadrant: str | None = None
    confidence_score: int
    ai_reasoning: str
    flags: dict | None = None
    icd10_codes: dict | None = None

    model_config = {"from_attributes": True}


class CodedEncounterResponse(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    review_status: str
    coded_procedures: list[CodedProcedureResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class OverrideProcedureRequest(BaseModel):
    cdt_code: str
    cdt_description: str
    override_reason: str
```

- [ ] **Step 2: Create API dependencies**

Create `src/buckteeth/api/deps.py`:

```python
import uuid
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from buckteeth.database import get_db


async def get_tenant_id(x_tenant_id: str = Header(...)) -> uuid.UUID:
    """Extract tenant ID from header. In production, this comes from JWT claims."""
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")


async def get_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session
```

- [ ] **Step 3: Commit**

```bash
git add src/buckteeth/api/
git commit -m "feat: add API schemas and dependency injection"
```

### Task 15: Patient API endpoints

**Files:**
- Create: `src/buckteeth/api/patients.py`
- Create: `tests/api/__init__.py`
- Create: `tests/api/test_patients.py`

- [ ] **Step 1: Write test for patient creation**

Create `tests/api/__init__.py` (empty) and `tests/api/test_patients.py`:

```python
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from buckteeth.main import app
from buckteeth.models.base import Base


TENANT_ID = str(uuid.uuid4())


@pytest.fixture
async def setup_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_tables):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_create_patient(client):
    response = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jane"
    assert "id" in data


async def test_get_patient(client):
    create_resp = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/v1/patients/{patient_id}",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["first_name"] == "Jane"


async def test_list_patients(client):
    await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    response = await client.get(
        "/v1/patients",
        headers={"X-Tenant-ID": TENANT_ID},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


async def test_tenant_isolation(client):
    other_tenant = str(uuid.uuid4())
    await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    response = await client.get(
        "/v1/patients",
        headers={"X-Tenant-ID": other_tenant},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_patients.py -v`
Expected: FAIL

- [ ] **Step 3: Implement patient endpoints**

Create `src/buckteeth/api/patients.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from buckteeth.api.deps import get_tenant_id, get_session
from buckteeth.api.schemas import PatientCreate, PatientResponse
from buckteeth.models.patient import Patient

router = APIRouter(prefix="/v1/patients", tags=["patients"])


@router.post("", status_code=201, response_model=PatientResponse)
async def create_patient(
    body: PatientCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    patient = Patient(tenant_id=tenant_id, **body.model_dump())
    session.add(patient)
    await session.flush()
    await session.refresh(patient)
    return patient


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Patient).where(Patient.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
```

- [ ] **Step 4: Register router in main.py**

Update `src/buckteeth/main.py` to include:

```python
from fastapi import FastAPI
from buckteeth.api.patients import router as patients_router

app = FastAPI(
    title="Buckteeth",
    description="AI-powered dental insurance coding agent",
    version="0.1.0",
)

app.include_router(patients_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/api/test_patients.py -v`
Expected: PASS (may need to wire up test DB override — see conftest)

- [ ] **Step 6: Commit**

```bash
git add src/buckteeth/api/patients.py src/buckteeth/main.py tests/api/
git commit -m "feat: add patient CRUD API endpoints with tenant isolation"
```

### Task 16: Encounter + coding API endpoints

**Files:**
- Create: `src/buckteeth/api/encounters.py`
- Create: `src/buckteeth/api/coding.py`
- Create: `tests/api/test_encounters.py`
- Create: `tests/api/test_coding.py`

- [ ] **Step 1: Write test for encounter creation from notes**

Create `tests/api/test_encounters.py`:

```python
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from buckteeth.main import app
from buckteeth.models.base import Base
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure

TENANT_ID = str(uuid.uuid4())


@pytest.fixture
async def setup_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_tables):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def patient_id(client):
    resp = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    return resp.json()["id"]


async def test_create_encounter_from_notes(client, patient_id):
    mock_parsed = ParsedEncounter(
        procedures=[
            ParsedProcedure(
                description="MOD composite restoration",
                tooth_numbers=[14],
                surfaces=["M", "O", "D"],
                diagnosis="recurrent decay",
            ),
        ]
    )
    with patch(
        "buckteeth.api.encounters.ClinicalNoteParser",
    ) as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=mock_parsed)
        response = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "MOD comp #14 recurrent decay",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "parsed"
    assert len(data["procedures"]) == 1
```

- [ ] **Step 2: Implement encounter endpoints**

Create `src/buckteeth/api/encounters.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from buckteeth.api.deps import get_tenant_id, get_session
from buckteeth.api.schemas import EncounterFromNotesRequest, EncounterResponse
from buckteeth.config import settings
from buckteeth.ingestion.text_parser import ClinicalNoteParser
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure

router = APIRouter(prefix="/v1/encounters", tags=["encounters"])


@router.post("/from-notes", status_code=201, response_model=EncounterResponse)
async def create_encounter_from_notes(
    body: EncounterFromNotesRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    parser = ClinicalNoteParser(api_key=settings.anthropic_api_key)
    parsed = await parser.parse(body.notes)

    encounter = ClinicalEncounter(
        tenant_id=tenant_id,
        patient_id=body.patient_id,
        provider_name=body.provider_name,
        date_of_service=body.date_of_service,
        raw_notes=body.notes,
        raw_input_type="text",
        status="parsed",
    )
    session.add(encounter)
    await session.flush()

    for proc in parsed.procedures:
        db_proc = ClinicalProcedure(
            tenant_id=tenant_id,
            encounter_id=encounter.id,
            description=proc.description,
            tooth_numbers={"teeth": proc.tooth_numbers} if proc.tooth_numbers else None,
            surfaces={"surfaces": proc.surfaces} if proc.surfaces else None,
            quadrant=proc.quadrant,
            diagnosis=proc.diagnosis,
        )
        session.add(db_proc)

    await session.flush()

    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter.id)
    )
    return result.scalar_one()


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter_id, ClinicalEncounter.tenant_id == tenant_id)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter
```

- [ ] **Step 3: Write test for coding endpoint**

Create `tests/api/test_coding.py`:

```python
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from buckteeth.main import app
from buckteeth.models.base import Base
from buckteeth.coding.schemas import CodingResult, CodeSuggestion
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure

TENANT_ID = str(uuid.uuid4())


@pytest.fixture
async def setup_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_tables):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def encounter_id(client):
    # Create patient
    resp = await client.post(
        "/v1/patients",
        json={"first_name": "Jane", "last_name": "Doe", "date_of_birth": "1990-01-15", "gender": "F"},
        headers={"X-Tenant-ID": TENANT_ID},
    )
    patient_id = resp.json()["id"]

    # Create encounter
    mock_parsed = ParsedEncounter(
        procedures=[ParsedProcedure(description="Adult prophylaxis")]
    )
    with patch("buckteeth.api.encounters.ClinicalNoteParser") as MockParser:
        instance = MockParser.return_value
        instance.parse = AsyncMock(return_value=mock_parsed)
        resp = await client.post(
            "/v1/encounters/from-notes",
            json={
                "patient_id": patient_id,
                "provider_name": "Dr. Smith",
                "date_of_service": "2026-03-12",
                "notes": "adult prophy",
            },
            headers={"X-Tenant-ID": TENANT_ID},
        )
    return resp.json()["id"]


async def test_code_encounter(client, encounter_id):
    mock_result = CodingResult(
        suggestions=[
            CodeSuggestion(
                cdt_code="D1110", cdt_description="Prophylaxis - adult",
                confidence_score=99, ai_reasoning="Standard adult prophylaxis",
            )
        ]
    )
    with patch("buckteeth.api.coding.CodingEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.code_encounter = AsyncMock(return_value=mock_result)
        response = await client.post(
            f"/v1/encounters/{encounter_id}/code",
            json={"payer_id": "delta_dental"},
            headers={"X-Tenant-ID": TENANT_ID},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["review_status"] == "pending"
    assert len(data["coded_procedures"]) == 1
    assert data["coded_procedures"][0]["cdt_code"] == "D1110"
```

- [ ] **Step 4: Implement coding endpoints**

Create `src/buckteeth/api/coding.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from buckteeth.api.deps import get_tenant_id, get_session
from buckteeth.api.schemas import CodeEncounterRequest, CodedEncounterResponse, OverrideProcedureRequest
from buckteeth.coding.engine import CodingEngine
from buckteeth.config import settings
from buckteeth.ingestion.schemas import ParsedEncounter, ParsedProcedure
from buckteeth.models.encounter import ClinicalEncounter, ClinicalProcedure
from buckteeth.models.coding import CodedEncounter, CodedProcedure

router = APIRouter(prefix="/v1/encounters", tags=["coding"])


@router.post("/{encounter_id}/code", status_code=201, response_model=CodedEncounterResponse)
async def code_encounter(
    encounter_id: uuid.UUID,
    body: CodeEncounterRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    # Load encounter with procedures
    result = await session.execute(
        select(ClinicalEncounter)
        .options(selectinload(ClinicalEncounter.procedures))
        .where(ClinicalEncounter.id == encounter_id, ClinicalEncounter.tenant_id == tenant_id)
    )
    encounter = result.scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Convert to ParsedEncounter for the coding engine
    parsed_procedures = []
    procedure_map: dict[int, ClinicalProcedure] = {}
    for i, proc in enumerate(encounter.procedures):
        parsed_procedures.append(ParsedProcedure(
            description=proc.description,
            tooth_numbers=proc.tooth_numbers.get("teeth") if proc.tooth_numbers else None,
            surfaces=proc.surfaces.get("surfaces") if proc.surfaces else None,
            quadrant=proc.quadrant,
            diagnosis=proc.diagnosis,
        ))
        procedure_map[i] = proc

    parsed_encounter = ParsedEncounter(procedures=parsed_procedures)

    # Run coding engine
    engine = CodingEngine(api_key=settings.anthropic_api_key)
    coding_result = await engine.code_encounter(parsed_encounter, payer_id=body.payer_id)

    # Save results
    coded_encounter = CodedEncounter(
        tenant_id=tenant_id,
        encounter_id=encounter_id,
    )
    session.add(coded_encounter)
    await session.flush()

    for i, suggestion in enumerate(coding_result.suggestions):
        clinical_proc = procedure_map.get(i, list(procedure_map.values())[0])
        coded_proc = CodedProcedure(
            tenant_id=tenant_id,
            coded_encounter_id=coded_encounter.id,
            clinical_procedure_id=clinical_proc.id,
            cdt_code=suggestion.cdt_code,
            cdt_description=suggestion.cdt_description,
            tooth_number=suggestion.tooth_number,
            surfaces=suggestion.surfaces,
            quadrant=suggestion.quadrant,
            confidence_score=suggestion.confidence_score,
            ai_reasoning=suggestion.ai_reasoning,
            flags={"flags": suggestion.flags} if suggestion.flags else None,
            icd10_codes={"codes": suggestion.icd10_codes} if suggestion.icd10_codes else None,
        )
        session.add(coded_proc)

    encounter.status = "coded"
    await session.flush()

    # Reload with relationships
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(CodedEncounter.id == coded_encounter.id)
    )
    return result.scalar_one()


@router.get("/{encounter_id}/coded", response_model=CodedEncounterResponse)
async def get_coded_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(CodedEncounter.encounter_id == encounter_id, CodedEncounter.tenant_id == tenant_id)
    )
    coded = result.scalar_one_or_none()
    if not coded:
        raise HTTPException(status_code=404, detail="Coded encounter not found")
    return coded


@router.post("/{encounter_id}/coded/approve", response_model=CodedEncounterResponse)
async def approve_coded_encounter(
    encounter_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(CodedEncounter)
        .options(selectinload(CodedEncounter.coded_procedures))
        .where(CodedEncounter.encounter_id == encounter_id, CodedEncounter.tenant_id == tenant_id)
    )
    coded = result.scalar_one_or_none()
    if not coded:
        raise HTTPException(status_code=404, detail="Coded encounter not found")
    coded.review_status = "approved"
    await session.flush()
    await session.refresh(coded)
    return coded
```

- [ ] **Step 5: Register routers in main.py**

Update `src/buckteeth/main.py`:

```python
from fastapi import FastAPI
from buckteeth.api.patients import router as patients_router
from buckteeth.api.encounters import router as encounters_router
from buckteeth.api.coding import router as coding_router

app = FastAPI(
    title="Buckteeth",
    description="AI-powered dental insurance coding agent",
    version="0.1.0",
)

app.include_router(patients_router)
app.include_router(encounters_router)
app.include_router(coding_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/buckteeth/api/ src/buckteeth/main.py tests/api/
git commit -m "feat: add encounter ingestion and coding API endpoints"
```

---

## Phase Summary

Phase 1 delivers:
- Project scaffolding with FastAPI, SQLAlchemy, Alembic
- Tenant-scoped database models (Patient, Encounter, Coding, Audit)
- CDT code reference database with 40+ seed codes
- Payer rules repository with frequency and bundling checks
- Claude-powered clinical note parser
- Claude-powered CDT code selector with RAG
- Coding engine with validation pipeline
- REST API for patients, encounters, and coding
- Full test coverage with mocked AI calls

## Future Phases

- **Phase 2:** Claim Builder + Narrative Generation
- **Phase 3:** Submission Gateway + Clearinghouse Integration
- **Phase 4:** Denial Management + Appeals
- **Phase 5:** React Frontend (Dentist + Front Desk views)
- **Phase 6:** Voice/Image Ingestion Pipelines
- **Phase 7:** PMS Adapter Layer
- **Phase 8:** Analytics Dashboard + Revenue Cycle
