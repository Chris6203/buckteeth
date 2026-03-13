# Phase 7: React Dashboard MVP

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a foundational React dashboard that connects to the existing FastAPI backend, providing patient management, claims tracking, and denial management screens.

**Architecture:** Vite-powered React + TypeScript SPA with React Router for navigation, Tailwind CSS for styling, and a typed API client layer. Backend gets CORS middleware. Vitest + React Testing Library for tests.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router v6, Vitest, React Testing Library

---

## File Structure

```
src/buckteeth/main.py              # Modify: add CORS middleware
frontend/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
├── postcss.config.js
├── tailwind.config.js
├── src/
│   ├── main.tsx                    # React entry point
│   ├── index.css                   # Tailwind CSS imports
│   ├── App.tsx                     # Router + layout wrapper
│   ├── api/
│   │   ├── client.ts              # Base fetch wrapper with tenant header
│   │   └── types.ts               # TypeScript interfaces matching backend schemas
│   ├── components/
│   │   ├── Layout.tsx             # Shell: sidebar + header + content area
│   │   └── StatusBadge.tsx        # Reusable color-coded status pill
│   ├── pages/
│   │   ├── Dashboard.tsx          # Home overview with summary cards
│   │   ├── Patients.tsx           # Patient list + create form
│   │   ├── Claims.tsx             # Claims list with status filtering
│   │   └── Denials.tsx            # Denials list + appeal generation
│   └── __tests__/
│       ├── setup.ts               # Test setup (jsdom, cleanup)
│       ├── client.test.ts         # API client unit tests
│       ├── Patients.test.tsx      # Patients page render test
│       ├── Claims.test.tsx        # Claims page render test
│       ├── Denials.test.tsx       # Denials page render test
│       └── Dashboard.test.tsx     # Dashboard page render test
```

---

## Chunk 1: Scaffolding & Core Infrastructure

### Task 1: Backend CORS + Frontend project scaffolding

**Files:**
- Modify: `src/buckteeth/main.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Add CORS middleware to FastAPI**

In `src/buckteeth/main.py`, add after the `app = FastAPI(...)` block:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Run backend tests to verify CORS doesn't break anything**

Run: `pytest tests/ -v --tb=short`
Expected: All 138 tests PASS

- [ ] **Step 3: Create `frontend/package.json`**

```json
{
  "name": "buckteeth-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.15",
    "typescript": "^5.6.3",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 4: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vitest/globals"],
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Create `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
```

- [ ] **Step 7: Create `frontend/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 8: Create `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 9: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Buckteeth</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 10: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

- [ ] **Step 11: Create `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 12: Create `frontend/src/App.tsx`**

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Patients from "./pages/Patients";
import Claims from "./pages/Claims";
import Denials from "./pages/Denials";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/claims" element={<Claims />} />
        <Route path="/denials" element={<Denials />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 13: Create placeholder page components**

Create `frontend/src/pages/Dashboard.tsx`:
```tsx
export default function Dashboard() {
  return <h1 className="text-2xl font-bold">Dashboard</h1>;
}
```

Create `frontend/src/pages/Patients.tsx`:
```tsx
export default function Patients() {
  return <h1 className="text-2xl font-bold">Patients</h1>;
}
```

Create `frontend/src/pages/Claims.tsx`:
```tsx
export default function Claims() {
  return <h1 className="text-2xl font-bold">Claims</h1>;
}
```

Create `frontend/src/pages/Denials.tsx`:
```tsx
export default function Denials() {
  return <h1 className="text-2xl font-bold">Denials</h1>;
}
```

- [ ] **Step 14: Create placeholder Layout component**

Create `frontend/src/components/Layout.tsx`:
```tsx
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div>
      <Outlet />
    </div>
  );
}
```

- [ ] **Step 15: Install dependencies and verify build**

```bash
cd frontend && npm install && npm run build
```
Expected: Build completes without errors.

- [ ] **Step 16: Commit**

```bash
git add src/buckteeth/main.py frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, React Router"
```

### Task 2: API client and TypeScript types

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/__tests__/setup.ts`
- Create: `frontend/src/__tests__/client.test.ts`

- [ ] **Step 1: Create `frontend/src/api/types.ts`**

TypeScript interfaces matching backend Pydantic schemas:

```typescript
// ── Patient ──────────────────────────────────────────────────────────

export interface PatientCreate {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  created_at: string | null;
}

// ── Encounter ────────────────────────────────────────────────────────

export interface ClinicalProcedure {
  id: string;
  description: string;
  tooth_numbers: number[] | null;
  surfaces: string[] | null;
  quadrant: string | null;
  diagnosis: string | null;
}

export interface Encounter {
  id: string;
  patient_id: string;
  provider_name: string;
  date_of_service: string;
  raw_notes: string | null;
  raw_input_type: string;
  status: string;
  procedures: ClinicalProcedure[];
  created_at: string | null;
}

export interface EncounterFromNotesRequest {
  patient_id: string;
  provider_name: string;
  date_of_service: string;
  notes: string;
}

// ── Coding ───────────────────────────────────────────────────────────

export interface CodedProcedure {
  id: string;
  cdt_code: string;
  cdt_description: string;
  tooth_number: string | null;
  surfaces: string | null;
  quadrant: string | null;
  confidence_score: number;
  ai_reasoning: string;
  flags: unknown;
  icd10_codes: unknown;
}

export interface CodedEncounter {
  id: string;
  encounter_id: string;
  review_status: string;
  coded_procedures: CodedProcedure[];
  created_at: string | null;
}

// ── Claims ───────────────────────────────────────────────────────────

export interface ClaimProcedure {
  id: string;
  cdt_code: string;
  cdt_description: string;
  tooth_number: string | null;
  surfaces: string | null;
  quadrant: string | null;
  fee_submitted: number | null;
}

export interface ClaimNarrative {
  id: string;
  cdt_code: string;
  narrative_text: string;
  generated_by: string;
  payer_tailored: boolean;
}

export interface Claim {
  id: string;
  patient_id: string;
  coded_encounter_id: string;
  provider_name: string;
  date_of_service: string;
  status: string;
  primary_payer_name: string;
  primary_payer_id: string;
  primary_subscriber_id: string;
  primary_group_number: string;
  secondary_payer_name: string | null;
  preauth_required: boolean;
  total_fee_submitted: number | null;
  procedures: ClaimProcedure[];
  narratives: ClaimNarrative[];
  created_at: string | null;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: string;
  risk_factors: string[];
  recommendations: string[];
}

// ── Submissions ──────────────────────────────────────────────────────

export interface Submission {
  id: string;
  claim_id: string;
  channel: string;
  clearinghouse_name: string | null;
  tracking_number: string | null;
  confirmation_number: string | null;
  status: string;
  error_message: string | null;
  created_at: string | null;
}

// ── Denials ──────────────────────────────────────────────────────────

export interface Denial {
  id: string;
  claim_id: string;
  denial_reason_code: string;
  denial_reason_description: string;
  denied_amount: number | null;
  payer_name: string;
  status: string;
  created_at: string | null;
}

export interface AppealDocument {
  id: string;
  denial_id: string;
  appeal_text: string;
  case_law_citations: unknown;
  generated_by: string;
  status: string;
  created_at: string | null;
}

export interface GenerateAppealRequest {
  clinical_notes: string;
  state: string;
}

// ── Health ────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
}
```

- [ ] **Step 2: Create `frontend/src/api/client.ts`**

```typescript
import type {
  Patient,
  PatientCreate,
  Encounter,
  EncounterFromNotesRequest,
  CodedEncounter,
  Claim,
  RiskAssessment,
  Submission,
  Denial,
  AppealDocument,
  GenerateAppealRequest,
  HealthResponse,
} from "./types";

const BASE = "";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001";

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Tenant-ID": localStorage.getItem("tenantId") ?? DEFAULT_TENANT,
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: headers(),
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

// ── Health ────────────────────────────────────────────────────────────

export const health = () => request<HealthResponse>("/health");

// ── Patients ─────────────────────────────────────────────────────────

export const listPatients = () => request<Patient[]>("/v1/patients");

export const createPatient = (data: PatientCreate) =>
  request<Patient>("/v1/patients", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getPatient = (id: string) => request<Patient>(`/v1/patients/${id}`);

// ── Encounters ───────────────────────────────────────────────────────

export const createEncounterFromNotes = (data: EncounterFromNotesRequest) =>
  request<Encounter>("/v1/encounters/from-notes", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getEncounter = (id: string) =>
  request<Encounter>(`/v1/encounters/${id}`);

// ── Coding ───────────────────────────────────────────────────────────

export const codeEncounter = (encounterId: string, payerId = "default") =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/code`, {
    method: "POST",
    body: JSON.stringify({ payer_id: payerId }),
  });

export const getCodedEncounter = (encounterId: string) =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/coded`);

export const approveCodedEncounter = (encounterId: string) =>
  request<CodedEncounter>(`/v1/encounters/${encounterId}/coded/approve`, {
    method: "POST",
  });

// ── Claims ───────────────────────────────────────────────────────────

export const listClaims = (status?: string) => {
  const qs = status ? `?status=${status}` : "";
  return request<Claim[]>(`/v1/claims${qs}`);
};

export const getClaim = (id: string) => request<Claim>(`/v1/claims/${id}`);

export const createClaim = (codedEncounterId: string) =>
  request<Claim>("/v1/claims", {
    method: "POST",
    body: JSON.stringify({ coded_encounter_id: codedEncounterId }),
  });

export const assessRisk = (claimId: string) =>
  request<RiskAssessment>(`/v1/claims/${claimId}/assess-risk`, {
    method: "POST",
    body: JSON.stringify({}),
  });

// ── Submissions ──────────────────────────────────────────────────────

export const submitClaim = (claimId: string) =>
  request<Submission>("/v1/submissions/submit", {
    method: "POST",
    body: JSON.stringify({ claim_id: claimId }),
  });

export const listSubmissions = () => request<Submission[]>("/v1/submissions");

// ── Denials ──────────────────────────────────────────────────────────

export const listDenials = (status?: string) => {
  const qs = status ? `?status=${status}` : "";
  return request<Denial[]>(`/v1/denials${qs}`);
};

export const getDenial = (id: string) => request<Denial>(`/v1/denials/${id}`);

export const generateAppeal = (denialId: string, data: GenerateAppealRequest) =>
  request<AppealDocument>(`/v1/denials/${denialId}/generate-appeal`, {
    method: "POST",
    body: JSON.stringify(data),
  });
```

- [ ] **Step 3: Create test setup**

Create `frontend/src/__tests__/setup.ts`:
```typescript
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
```

Update `frontend/vite.config.ts` — replace entire file:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/__tests__/setup.ts",
  },
});
```

- [ ] **Step 4: Create `frontend/src/__tests__/client.test.ts`**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking fetch
import { listPatients, createPatient, health } from "../api/client";

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

describe("API client", () => {
  it("health check calls /health", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "healthy", version: "0.1.0" }),
    });

    const result = await health();
    expect(result.status).toBe("healthy");
    expect(mockFetch).toHaveBeenCalledWith(
      "/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Tenant-ID": expect.any(String),
        }),
      }),
    );
  });

  it("listPatients calls /v1/patients", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "abc", first_name: "Jane" }],
    });

    const patients = await listPatients();
    expect(patients).toHaveLength(1);
    expect(patients[0].first_name).toBe("Jane");
  });

  it("createPatient sends POST with body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "new-id", first_name: "John" }),
    });

    await createPatient({
      first_name: "John",
      last_name: "Doe",
      date_of_birth: "1990-01-01",
      gender: "M",
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "/v1/patients",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("John"),
      }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found" }),
    });

    await expect(listPatients()).rejects.toThrow("Not found");
  });

  it("uses tenant ID from localStorage", async () => {
    localStorage.setItem("tenantId", "custom-tenant-id");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    await listPatients();

    expect(mockFetch).toHaveBeenCalledWith(
      "/v1/patients",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Tenant-ID": "custom-tenant-id",
        }),
      }),
    );
  });
});
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx vitest run
```
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/ frontend/src/__tests__/ frontend/vite.config.ts
git commit -m "feat: add typed API client with tests"
```

### Task 3: Layout shell and StatusBadge component

**Files:**
- Create: `frontend/src/components/Layout.tsx` (overwrite placeholder)
- Create: `frontend/src/components/StatusBadge.tsx`

- [ ] **Step 1: Implement Layout with sidebar navigation**

Overwrite `frontend/src/components/Layout.tsx`:

```tsx
import { NavLink, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/patients", label: "Patients", icon: "👤" },
  { to: "/claims", label: "Claims", icon: "📋" },
  { to: "/denials", label: "Denials", icon: "⚠️" },
] as const;

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <nav className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-blue-600">Buckteeth</h1>
          <p className="text-xs text-gray-500">Dental Coding Agent</p>
        </div>
        <ul className="flex-1 py-2">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-700 font-medium border-r-2 border-blue-700"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  }`
                }
              >
                <span>{icon}</span>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="p-4 border-t border-gray-200 text-xs text-gray-400">
          v0.1.0
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create StatusBadge component**

Create `frontend/src/components/StatusBadge.tsx`:

```tsx
const STATUS_COLORS: Record<string, string> = {
  // Claims
  draft: "bg-gray-100 text-gray-700",
  ready: "bg-blue-100 text-blue-700",
  submitted: "bg-yellow-100 text-yellow-700",
  accepted: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
  paid: "bg-green-100 text-green-700",
  // Denials
  appealed: "bg-purple-100 text-purple-700",
  overturned: "bg-green-100 text-green-700",
  upheld: "bg-red-100 text-red-700",
  // Encounters
  parsed: "bg-blue-100 text-blue-700",
  coded: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
};

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors}`}
    >
      {status}
    </span>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: add layout shell with sidebar navigation and StatusBadge"
```

---

## Chunk 2: Page Components

### Task 4: Patients page

**Files:**
- Modify: `frontend/src/pages/Patients.tsx`
- Create: `frontend/src/__tests__/Patients.test.tsx`

- [ ] **Step 1: Write test for Patients page**

Create `frontend/src/__tests__/Patients.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import Patients from "../pages/Patients";

vi.mock("../api/client", () => ({
  listPatients: vi.fn().mockResolvedValue([
    {
      id: "p1",
      first_name: "Jane",
      last_name: "Smith",
      date_of_birth: "1985-03-15",
      gender: "F",
      created_at: null,
    },
    {
      id: "p2",
      first_name: "John",
      last_name: "Doe",
      date_of_birth: "1972-07-22",
      gender: "M",
      created_at: null,
    },
  ]),
  createPatient: vi.fn().mockResolvedValue({
    id: "p3",
    first_name: "New",
    last_name: "Patient",
    date_of_birth: "2000-01-01",
    gender: "F",
    created_at: null,
  }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Patients />
    </BrowserRouter>,
  );
}

describe("Patients page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders patient list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Patients")).toBeInTheDocument();
  });
});
```

- [ ] **Step 1b: Add `@testing-library/user-event` to devDependencies**

Run:
```bash
cd frontend && npm install --save-dev @testing-library/user-event@^14.5.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/__tests__/Patients.test.tsx
```
Expected: FAIL — Patients page is still a placeholder with just "Patients" heading.

- [ ] **Step 3: Implement Patients page**

Overwrite `frontend/src/pages/Patients.tsx`:

```tsx
import { useEffect, useState } from "react";
import { listPatients, createPatient } from "../api/client";
import type { Patient, PatientCreate } from "../api/types";

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadPatients();
  }, []);

  async function loadPatients() {
    try {
      setLoading(true);
      const data = await listPatients();
      setPatients(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load patients");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(data: PatientCreate) {
    try {
      await createPatient(data);
      setShowForm(false);
      await loadPatients();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create patient");
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Patients</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          {showForm ? "Cancel" : "Add Patient"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {showForm && <CreatePatientForm onSubmit={handleCreate} />}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : patients.length === 0 ? (
        <p className="text-gray-500">No patients found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  DOB
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Gender
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {patients.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {p.first_name} {p.last_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {p.date_of_birth}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {p.gender}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function CreatePatientForm({
  onSubmit,
}: {
  onSubmit: (data: PatientCreate) => void;
}) {
  const [form, setForm] = useState<PatientCreate>({
    first_name: "",
    last_name: "",
    date_of_birth: "",
    gender: "",
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white rounded-lg border border-gray-200 p-4 mb-6"
    >
      <div className="grid grid-cols-2 gap-4">
        <input
          placeholder="First name"
          value={form.first_name}
          onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          placeholder="Last name"
          value={form.last_name}
          onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <input
          type="date"
          value={form.date_of_birth}
          onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        />
        <select
          value={form.gender}
          onChange={(e) => setForm({ ...form, gender: e.target.value })}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          required
        >
          <option value="">Gender</option>
          <option value="M">Male</option>
          <option value="F">Female</option>
          <option value="O">Other</option>
        </select>
      </div>
      <button
        type="submit"
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
      >
        Create Patient
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run
```
Expected: All tests PASS (client tests + Patients tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Patients page with list and create form"
```

### Task 5: Claims page

**Files:**
- Modify: `frontend/src/pages/Claims.tsx`
- Create: `frontend/src/__tests__/Claims.test.tsx`

- [ ] **Step 1: Write test**

Create `frontend/src/__tests__/Claims.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Claims from "../pages/Claims";

vi.mock("../api/client", () => ({
  listClaims: vi.fn().mockResolvedValue([
    {
      id: "c1",
      patient_id: "p1",
      coded_encounter_id: "ce1",
      provider_name: "Dr. Smith",
      date_of_service: "2026-03-12",
      status: "draft",
      primary_payer_name: "Delta Dental",
      primary_payer_id: "DD001",
      primary_subscriber_id: "SUB-001",
      primary_group_number: "GRP-100",
      secondary_payer_name: null,
      preauth_required: false,
      total_fee_submitted: 300.0,
      procedures: [],
      narratives: [],
      created_at: null,
    },
  ]),
  submitClaim: vi.fn(),
  assessRisk: vi.fn(),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Claims />
    </BrowserRouter>,
  );
}

describe("Claims page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders claims list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
      expect(screen.getByText("Delta Dental")).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Claims")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/__tests__/Claims.test.tsx
```
Expected: FAIL — Claims page is still a placeholder.

- [ ] **Step 3: Implement Claims page**

Overwrite `frontend/src/pages/Claims.tsx`:

```tsx
import { useEffect, useState } from "react";
import { listClaims, submitClaim, assessRisk } from "../api/client";
import type { Claim, RiskAssessment } from "../api/types";
import StatusBadge from "../components/StatusBadge";

const STATUS_FILTERS = ["all", "draft", "ready", "submitted", "accepted", "denied", "paid"];

export default function Claims() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [riskResult, setRiskResult] = useState<{
    claimId: string;
    assessment: RiskAssessment;
  } | null>(null);

  useEffect(() => {
    loadClaims();
  }, [filter]);

  async function loadClaims() {
    try {
      setLoading(true);
      const data = await listClaims(filter === "all" ? undefined : filter);
      setClaims(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(claimId: string) {
    try {
      await submitClaim(claimId);
      await loadClaims();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit claim");
    }
  }

  async function handleAssessRisk(claimId: string) {
    try {
      const assessment = await assessRisk(claimId);
      setRiskResult({ claimId, assessment });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assess risk");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Claims</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-2 text-sm capitalize transition-colors ${
              filter === s
                ? "border-b-2 border-blue-600 text-blue-600 font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Risk assessment result */}
      {riskResult && (
        <div className="mb-4 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Risk Assessment</h3>
            <button
              onClick={() => setRiskResult(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span>
              Score: <strong>{riskResult.assessment.risk_score}</strong>
            </span>
            <StatusBadge status={riskResult.assessment.risk_level} />
          </div>
          {riskResult.assessment.risk_factors.length > 0 && (
            <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
              {riskResult.assessment.risk_factors.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : claims.length === 0 ? (
        <p className="text-gray-500">No claims found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Provider
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Amount
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {claims.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {c.provider_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.date_of_service}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.primary_payer_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {c.total_fee_submitted
                      ? `$${c.total_fee_submitted.toFixed(2)}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex gap-2">
                      {c.status === "draft" && (
                        <button
                          onClick={() => handleSubmit(c.id)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          Submit
                        </button>
                      )}
                      <button
                        onClick={() => handleAssessRisk(c.id)}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        Risk
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Claims page with status filtering and risk assessment"
```

### Task 6: Denials page

**Files:**
- Modify: `frontend/src/pages/Denials.tsx`
- Create: `frontend/src/__tests__/Denials.test.tsx`

- [ ] **Step 1: Write test**

Create `frontend/src/__tests__/Denials.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Denials from "../pages/Denials";

vi.mock("../api/client", () => ({
  listDenials: vi.fn().mockResolvedValue([
    {
      id: "d1",
      claim_id: "c1",
      denial_reason_code: "D0001",
      denial_reason_description: "Not medically necessary",
      denied_amount: 500.0,
      payer_name: "Delta Dental",
      status: "denied",
      created_at: null,
    },
  ]),
  generateAppeal: vi.fn().mockResolvedValue({
    id: "a1",
    denial_id: "d1",
    appeal_text: "Appeal letter text...",
    case_law_citations: [],
    generated_by: "ai",
    status: "draft",
    created_at: null,
  }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Denials />
    </BrowserRouter>,
  );
}

describe("Denials page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders denials list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Delta Dental")).toBeInTheDocument();
      expect(
        screen.getByText("Not medically necessary"),
      ).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Denials")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/__tests__/Denials.test.tsx
```
Expected: FAIL — Denials page is still a placeholder.

- [ ] **Step 3: Implement Denials page**

Overwrite `frontend/src/pages/Denials.tsx`:

```tsx
import { useEffect, useState } from "react";
import { listDenials, generateAppeal } from "../api/client";
import type { Denial, AppealDocument } from "../api/types";
import StatusBadge from "../components/StatusBadge";

export default function Denials() {
  const [denials, setDenials] = useState<Denial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appealResult, setAppealResult] = useState<AppealDocument | null>(null);
  const [appealingId, setAppealingId] = useState<string | null>(null);

  useEffect(() => {
    loadDenials();
  }, []);

  async function loadDenials() {
    try {
      setLoading(true);
      const data = await listDenials();
      setDenials(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load denials");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateAppeal(denialId: string) {
    try {
      setAppealingId(denialId);
      const appeal = await generateAppeal(denialId, {
        clinical_notes: "Patient required treatment as documented.",
        state: "CA",
      });
      setAppealResult(appeal);
      await loadDenials();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate appeal",
      );
    } finally {
      setAppealingId(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Denials</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Appeal result */}
      {appealResult && (
        <div className="mb-4 p-4 bg-white rounded-lg border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium">Generated Appeal</h3>
            <button
              onClick={() => setAppealResult(null)}
              className="text-gray-400 hover:text-gray-600 text-sm"
            >
              Dismiss
            </button>
          </div>
          <div className="text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-auto">
            {appealResult.appeal_text}
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : denials.length === 0 ? (
        <p className="text-gray-500">No denials found.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payer
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Reason
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Amount
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {denials.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {d.payer_name}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {d.denial_reason_description}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {d.denied_amount ? `$${d.denied_amount.toFixed(2)}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {d.status === "denied" && (
                      <button
                        onClick={() => handleGenerateAppeal(d.id)}
                        disabled={appealingId === d.id}
                        className="text-blue-600 hover:text-blue-800 disabled:text-gray-400"
                      >
                        {appealingId === d.id ? "Generating..." : "Generate Appeal"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run
```
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add Denials page with appeal generation"
```

### Task 7: Dashboard home page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/__tests__/Dashboard.test.tsx`

- [ ] **Step 1: Write Dashboard test**

Create `frontend/src/__tests__/Dashboard.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard";

vi.mock("../api/client", () => ({
  listPatients: vi.fn().mockResolvedValue([{ id: "p1" }, { id: "p2" }]),
  listClaims: vi.fn().mockResolvedValue([{ id: "c1" }]),
  listDenials: vi.fn().mockResolvedValue([{ id: "d1" }, { id: "d2" }, { id: "d3" }]),
  health: vi.fn().mockResolvedValue({ status: "healthy", version: "0.1.0" }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>,
  );
}

describe("Dashboard page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders summary cards with counts", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // patients
      expect(screen.getByText("1")).toBeInTheDocument(); // claims
      expect(screen.getByText("3")).toBeInTheDocument(); // denials
    });
  });

  it("shows API connected status", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Connected/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npx vitest run src/__tests__/Dashboard.test.tsx
```
Expected: FAIL — Dashboard page is still a placeholder.

- [ ] **Step 3: Implement Dashboard with summary cards**

Overwrite `frontend/src/pages/Dashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPatients, listClaims, listDenials, health } from "../api/client";

interface Stats {
  patients: number;
  claims: number;
  denials: number;
  healthy: boolean;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [patients, claims, denials, h] = await Promise.all([
          listPatients().catch(() => []),
          listClaims().catch(() => []),
          listDenials().catch(() => []),
          health().catch(() => ({ status: "unhealthy" })),
        ]);
        setStats({
          patients: patients.length,
          claims: claims.length,
          denials: denials.length,
          healthy: h.status === "healthy",
        });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return <p className="text-gray-500">Loading dashboard...</p>;
  }

  const cards = [
    {
      label: "Patients",
      count: stats?.patients ?? 0,
      link: "/patients",
      color: "bg-blue-50 text-blue-700",
    },
    {
      label: "Claims",
      count: stats?.claims ?? 0,
      link: "/claims",
      color: "bg-green-50 text-green-700",
    },
    {
      label: "Denials",
      count: stats?.denials ?? 0,
      link: "/denials",
      color: "bg-red-50 text-red-700",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* API health indicator */}
      <div className="mb-6 flex items-center gap-2 text-sm">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            stats?.healthy ? "bg-green-500" : "bg-red-500"
          }`}
        />
        <span className="text-gray-500">
          API: {stats?.healthy ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((card) => (
          <Link
            key={card.label}
            to={card.link}
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
          >
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className={`text-3xl font-bold mt-1 ${card.color}`}>
              {card.count}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run all frontend tests**

```bash
cd frontend && npx vitest run
```
Expected: All tests PASS.

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```
Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/__tests__/Dashboard.test.tsx
git commit -m "feat: add Dashboard home page with summary cards"
```

---

## Phase 7 Summary

Phase 7 delivers:
- CORS middleware on FastAPI backend
- Vite + React + TypeScript + Tailwind project scaffolding
- Typed API client with full backend endpoint coverage
- Layout shell with sidebar navigation
- Dashboard home page with summary cards and API health check
- Patients page with list table and create form
- Claims page with status filter tabs, submit action, and risk assessment
- Denials page with list and AI appeal generation
- StatusBadge reusable component
- Vitest tests for API client and all pages
