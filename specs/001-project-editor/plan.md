# Implementation Plan: Project Editor

**Branch**: `001-project-editor` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-project-editor/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A stateless FastAPI backend in `backend/` sits between the browser and the upstream records API.
It exposes a slim project list, a reduced edit DTO, and a save endpoint that takes `{base, changes}`.
On every save it re-reads the upstream record and runs a pure three-way merge (`base`, `mine`,
`theirs`): non-overlapping changes are merged, same-field changes answer `409` with both values,
and the upstream `PUT` body is built from the fresh upstream record plus the merged fields, so
`linked_companies` always survives. Ambiguous `504`s are reconciled by reading the record back,
with one automatic retry that goes through the merge again. A Vite + React + MUI frontend in
`frontend/` provides the list page, the edit page and the conflict dialog. No database, no cache,
no locks.

## Technical Context

**Language/Version**: Python ≥ 3.12 (backend); TypeScript, `strict: true` (frontend)

**Primary Dependencies**: FastAPI, uvicorn, httpx (backend); React, MUI (`@mui/material`,
`@emotion/react`, `@emotion/styled`), `react-router-dom`, Vite (frontend)

**Storage**: N/A — the tool persists nothing; the upstream is the only store

**Testing**: pytest against the real upstream app mounted in-process with a fixed random generator
(backend); Vitest for the one pure module (frontend)

**Target Platform**: Linux server, three instances behind a load balancer (backend); current
desktop browsers (frontend). Locally: macOS, one instance each

**Project Type**: Web application (backend + frontend)

**Performance Goals**: list and project load are one upstream call each. A save is at most 3
upstream reads and 2 writes; about 6 s in the worst documented case (every read slow, one retry)

**Constraints**: no correctness state in the backend process; the browser reaches only `/api`;
`upstream/` is never modified; upstream read timeout 5 s, connect timeout 2 s

**Scale/Scope**: ~30 projects, a handful of concurrent editors, 2 screens and 1 dialog, 3 endpoints

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Upstream Is Untouchable | Nothing under `upstream/` is edited; it is only a dev-time path dependency for tests. The browser calls `/api` only (Vite proxy in dev). The API key is read from the backend's environment and appears in no response or bundle | Pass |
| II. Stateless Backend | The base for conflict detection travels in the request. Every save starts with a fresh upstream read. The only process-level object is the httpx connection pool, which holds nothing about records | Pass |
| III. No Silent Overwrites | Same-field conflicts answer `409` and write nothing. Key-date identity is defined in the spec (FR-015/016). A `504` is never reported without a read-back; the retry re-runs the merge | Pass |
| IV. Honest Scope | Three endpoints, two pages, one dialog. Dependencies are listed with reasons in research R9. Cuts and the two known limits (check-then-write window, late-applied writes) are marked for `DECISIONS.md` | Pass |
| V. Tests Pin Behaviour | `test_merge.py` for the pure merge; `test_save.py` for conflict scenarios and every `504` branch using `create_app(rng=FixedRandom(...))`; no coverage target | Pass |

**Post-design re-check (after Phase 1)**: Pass, no violations. Two points were checked again:

- The `409` body carries `current` and `merged` in addition to the `conflicts` list given in the
  planning input. This keeps the merge in one place (backend) instead of duplicating it in the
  browser; it adds no server state (research R2).
- FR-025's read-back adds one upstream read to every successful save. Accepted in clarification Q2.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-editor/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and alternatives
├── data-model.md        # Phase 1: DTOs, merge model, save lifecycle
├── quickstart.md        # Phase 1: how to run and validate
├── contracts/
│   └── api.md           # Phase 1: backend ↔ browser contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml       # uv project; dev deps: pytest, ruff, pyright, records-api (path ../upstream)
├── .env.example         # UPSTREAM_BASE_URL, UPSTREAM_API_KEY
├── app/
│   ├── main.py          # create_app(): lifespan (httpx client), the three routes, error mapping
│   ├── config.py        # reads the two environment variables
│   ├── models.py        # ProjectSummary, KeyDate, EditableProject, SaveRequest, Conflict, SaveResult
│   ├── upstream.py      # UpstreamClient: list / get / put, with typed outcomes for 404, 504, errors
│   ├── merge.py         # merge(base, mine, theirs) — pure, no I/O
│   └── save.py          # save_project(): read → merge → write → read back → reconcile / retry once
└── tests/
    ├── conftest.py      # FixedRandom, in-process upstream, app + TestClient fixtures
    ├── test_merge.py    # merge rules, key-date identity, duplicate-label fallback
    ├── test_save.py     # two-editor and import scenarios; every 504 branch
    └── test_api.py      # list/detail DTO shapes, 404/422/502 mapping, enum parity with upstream

frontend/
├── package.json         # pnpm; scripts: dev, build, lint, test
├── vite.config.ts       # proxy /api → http://127.0.0.1:8000
├── index.html
└── src/
    ├── main.tsx         # router: "/" and "/projects/:id"
    ├── types.ts         # DTO types, SECTORS, STAGES
    ├── api.ts           # fetch wrappers returning the SaveResult union
    ├── edit.ts          # pure: validate form, apply conflict choices to `merged`
    ├── edit.test.ts
    ├── pages/
    │   ├── ProjectListPage.tsx
    │   └── ProjectEditPage.tsx
    └── components/
        ├── KeyDatesEditor.tsx
        └── ConflictDialog.tsx

upstream/                # not ours; never modified
```

**Structure Decision**: Web application with `backend/` and `frontend/` at the repository root
beside the untouched `upstream/`. The backend is deliberately flat (six modules, no layers): the
two modules that carry the risk, `merge.py` and `save.py`, are isolated so they can be read and
extended on their own. The frontend keeps all non-visual logic in `edit.ts` and `api.ts`.

### Requirement → module map

| Requirements | Where |
|---|---|
| FR-001 – FR-003 (list, detail, slim DTOs) | `main.py`, `models.py`, `ProjectListPage.tsx` |
| FR-004 – FR-006 (edit, validation) | `models.py`, `save.py` (duplicate-label rule), `edit.ts`, `ProjectEditPage.tsx`, `KeyDatesEditor.tsx` |
| FR-007 (pass-through fields) | `save.py` (body built from the fresh read) |
| FR-008 – FR-016 (merge and conflicts) | `merge.py` |
| FR-013, FR-017 (resolve, merged notice) | `ConflictDialog.tsx`, `edit.ts`, `ProjectEditPage.tsx` |
| FR-018 (stateless) | whole backend; demonstrated by quickstart step 10 |
| FR-019, FR-023 (loading, errors, edits kept) | `ProjectListPage.tsx`, `ProjectEditPage.tsx` |
| FR-020 – FR-022, FR-025 (504, retry, read-back) | `save.py`, `upstream.py` |
| FR-024 (browser boundary, key) | `config.py`, `vite.config.ts` |

## Complexity Tracking

No constitution violations; nothing to justify.
