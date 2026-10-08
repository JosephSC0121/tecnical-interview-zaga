---

description: "Task list for the Project Editor feature"
---

# Tasks: Project Editor

**Input**: Design documents from `/specs/001-project-editor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Included. Constitution principle V requires pytest tests for the merge and conflict logic
and for `504` handling, written before the implementation where viable. Frontend tests are limited
to the one pure module, `edit.ts`.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Every task names the files it touches

## Path Conventions

Web application: `backend/app/`, `backend/tests/`, `frontend/src/`. Nothing under `upstream/` is
ever edited (a hook blocks it).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Two empty, runnable projects with lint, type-check and test commands working.

- [X] T001 Create `backend/pyproject.toml` as a uv project (`requires-python = ">=3.12"`, `[tool.uv] package = false`) with dependencies `fastapi`, `uvicorn`, `httpx`; dev group `pytest`, `ruff`, `pyright`, `records-api`; `[tool.uv.sources] records-api = { path = "../upstream" }`; `[tool.pytest.ini_options] testpaths = ["tests"], pythonpath = ["."]`; ruff line length 100. Create empty `backend/app/__init__.py`. Run `uv sync` in `backend/` and confirm `uv run python -c "import records_api, fastapi, httpx"` works
- [X] T002 [P] Create `backend/.env.example` with `UPSTREAM_BASE_URL=http://127.0.0.1:8081` and `UPSTREAM_API_KEY=local-dev-key`, each with a one-line comment
- [X] T003 [P] Scaffold `frontend/` with the Vite `react-ts` template using pnpm; add `@mui/material`, `@emotion/react`, `@emotion/styled`, `react-router-dom`; add dev dependency `vitest`; set scripts `dev`, `build`, `lint`, `test` (`vitest run`) in `frontend/package.json`; confirm `strict: true` in the tsconfig; delete the template's demo component, assets and CSS
- [X] T004 Configure `frontend/vite.config.ts`: dev-server proxy `/api` → `http://127.0.0.1:8000`, and the Vitest `test` block (node environment)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pieces every story needs: config, shared DTOs, the upstream reader, the app
factory, the test harness, and the frontend shell.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create `backend/app/config.py`: a frozen `Settings` dataclass and `load_settings()` reading `UPSTREAM_BASE_URL` (default `http://127.0.0.1:8081`) and `UPSTREAM_API_KEY` (required; raise a clear error naming the variable if missing). No key value in source
- [X] T006 [P] Create `backend/app/models.py` with the shared DTOs from data-model.md: `Sector` = Literal `energy`, `mining`, `water`, `transport`, `oil_and_gas`, `ict`; `Stage` = Literal `idea`, `feasibility`, `tender`, `financing`, `construction`, `operation`, `cancelled`; `KeyDate` (`label`: "non-empty after trimming", `date`: "valid calendar date", `YYYY-MM-DD`); `ProjectSummary` (`id`, `name`, `sector`, `country`, `stage`); `EditableProject` (`name`: "non-empty", `sector`, `country`: "non-empty", `stage`, `key_dates: list[KeyDate]`); `ProjectDetail` = `EditableProject` plus `id`; `UpstreamRecord` = `id`, the five form fields and `linked_companies: list[dict]`, used only to check what the upstream returns. Models ignore extra fields so they can be built straight from an upstream record
- [X] T007 Create `backend/app/upstream.py`: `UpstreamClient` wrapping an injected `httpx.AsyncClient`, with `list_projects() -> list[dict]` and `get_project(id) -> dict`; exceptions `ProjectNotFound` (upstream `404`) and `UpstreamError` (any other non-2xx, transport error or timeout). Every record returned is validated against `UpstreamRecord`; a record that does not validate (for example an unknown `sector`) raises `UpstreamError("upstream returned an invalid record")`, so it surfaces as `502` and never as `500`. One invalid record fails the whole list. Add `build_http_client(settings)` returning an `httpx.AsyncClient` with `base_url`, header `X-Api-Key`, and `httpx.Timeout(5.0, connect=2.0)`
- [X] T008 Create `backend/app/main.py`: `create_app(http_client: httpx.AsyncClient | None = None) -> FastAPI`. When no client is passed, the lifespan builds one from `load_settings()` and closes it on shutdown. Register exception handlers: `ProjectNotFound` → `404 {"detail": ...}`, `UpstreamError` → `502 {"detail": ...}`. No routes yet. (depends on T005, T007)
- [X] T009 Create `backend/tests/conftest.py`: `FixedRandom(random.Random)` whose `random()` pops given values in turn; an `UpstreamSpy` httpx transport wrapping `httpx.ASGITransport(app=records_api.main.create_app(rng=...))` that records every `(method, path)` in `calls`, supports `after_call(n, callback)` to run a callback right after the n-th upstream call, `fail_from(n)` to raise `httpx.ConnectError` from the n-th call on, `fail_call(n)` to raise it for the n-th call only, and `respond_call(n, response)` to answer the n-th call with a canned `httpx.Response` instead of reaching the upstream; fixtures `upstream` (env `UPSTREAM_SLOW_RATE=0`, `UPSTREAM_TIMEOUT_RATE=0`, returns the spy plus a direct `TestClient` to the upstream app for playing "the other writer"), `flaky_upstream(*values)` (timeout rate `0.1`, `FixedRandom(*values)`), and `client` (FastAPI `TestClient` over our `create_app(http_client=...)` built on the spy with the `X-Api-Key` header). (depends on T008)
- [X] T010 [P] Create `frontend/src/types.ts`: `SECTORS` and `STAGES` const arrays with the same values as T006, and types `Sector`, `Stage`, `KeyDate`, `ProjectSummary`, `EditableProject`, `ProjectDetail`
- [X] T011 [P] Create `frontend/src/api.ts` with a private `request()` helper around `fetch` for `/api` paths that throws an `ApiError` carrying status and detail for non-2xx responses and for network failures
- [X] T012 Replace `frontend/src/main.tsx` with the app shell: MUI `CssBaseline`, a `Container`, and `react-router-dom` routes `/` and `/projects/:id` pointing at placeholder pages `frontend/src/pages/ProjectListPage.tsx` and `frontend/src/pages/ProjectEditPage.tsx`. `pnpm dev` must render without errors

**Checkpoint**: `uv run pytest` collects with no errors, `uv run pyright` and `pnpm exec tsc --noEmit` pass.

---

## Phase 3: User Story 1 - List projects (Priority: P1) 🎯 MVP

**Goal**: An editor sees all projects with id, name, sector, country and stage, and opens one.

**Independent Test**: With the upstream on seed data, the list shows 30 projects with five columns
and clicking a row opens that project with its current values (quickstart step 1).

### Tests for User Story 1

> Write these first and confirm they fail before implementing.

- [X] T013 [P] [US1] Write `backend/tests/test_api.py`: `GET /api/projects` returns 30 items whose keys are exactly `id`, `name`, `sector`, `country`, `stage`; `GET /api/projects/P-1001` returns exactly `id`, `name`, `sector`, `country`, `stage`, `key_dates` (no `linked_companies`, no read-only fields); unknown id → `404`; upstream unreachable (`fail_from(1)`) → `502` on both endpoints; an upstream record with an unknown `sector` (`respond_call`) → `502` on both endpoints; no response body contains the API key; `Sector` and `Stage` literals in `app.models` equal the upstream's `SECTORS` keys and `STAGES`

### Implementation for User Story 1

- [X] T014 [US1] Add routes to `backend/app/main.py`: `GET /api/projects` → `list[ProjectSummary]` and `GET /api/projects/{project_id}` → `ProjectDetail`, both built from `UpstreamClient` results. Make T013 pass
- [X] T015 [P] [US1] Add `listProjects(): Promise<ProjectSummary[]>` and `getProject(id): Promise<ProjectDetail>` to `frontend/src/api.ts`
- [X] T016 [US1] Implement `frontend/src/pages/ProjectListPage.tsx`: MUI table with columns id, name, sector, country, stage; each row links to `/projects/:id`; a loading indicator while fetching; on error an `Alert` with a Retry button instead of an empty table (FR-001, FR-019, US1 scenario 3)
- [X] T017 [US1] Implement loading in `frontend/src/pages/ProjectEditPage.tsx`: fetch the project by route id; loading indicator visible until the form is ready; "not found" state with a link back to the list for `404`; error `Alert` with Retry for other failures; on success render controlled inputs for name, country (text), sector, stage (selects from `SECTORS`/`STAGES`) and a read-only list of key dates. Keep `base` (the loaded `EditableProject`) and `form` in state. No save yet

**Checkpoint**: User Story 1 works end to end against the running upstream and backend.

---

## Phase 4: User Story 2 - Edit a project (Priority: P1)

**Goal**: Change name, sector, country, stage and key dates (add, edit, remove) and save, with
everything the form does not show left exactly as it was.

**Independent Test**: Edit each core field and add, change and remove a key date on one project,
save, reload, and confirm the changes are stored and `linked_companies` upstream is unchanged
(quickstart step 2).

### Tests for User Story 2

- [X] T018 [P] [US2] Write `backend/tests/test_save.py` (single-editor section): changing `name` and `stage` stores both and leaves every other upstream field equal; changing one key date, removing one and adding one stores exactly the resulting set; `linked_companies` after a save equals the upstream value at save time, including when the test changed `linked_companies` directly upstream after "loading" `base`; a request whose `changes` is empty or equal to `base` answers `200` `status: "unchanged"` and the spy shows no `PUT`; unknown id → `404`; `422` for empty `name`, empty `country`, unknown `sector` or `stage`, key date with empty label, key date with invalid date, an upstream `422` on the `PUT` (`respond_call`) answered as `422` carrying the upstream's detail, and two key dates with the same label ignoring case and surrounding spaces when the list differs from `base`; a `base` that already contains duplicate labels with an unchanged list and a changed `name` is accepted
- [X] T019 [P] [US2] Write `frontend/src/edit.test.ts` for `validateForm`: errors keyed by field for empty name, empty country, key date with empty label, key date with empty date, and duplicate labels ignoring case and surrounding spaces when the key dates differ from `base`; no duplicate-label error when the list is unchanged from a `base` that already has duplicates; no errors for a valid form

### Implementation for User Story 2

- [X] T020 [US2] Extend `backend/app/models.py`: `ProjectChanges` (every `EditableProject` field optional, same field rules: `name` and `country` "non-empty" when present); `SaveRequest` (`base: EditableProject`, `changes: ProjectChanges`); result models `Saved` (`status: "saved"`, `project: ProjectDetail`, `merged_with_others: bool`) and `Unchanged` (`status: "unchanged"`, `project: ProjectDetail`)
- [X] T021 [US2] Add `put_project(id, body: dict) -> dict` to `backend/app/upstream.py`, raising `ProjectNotFound` on `404`, `UpstreamRejected(detail)` on `422` (carrying the upstream's `detail`), and `UpstreamError` otherwise (ambiguity handling comes in US4)
- [X] T022 [US2] Create `backend/app/save.py` with `save_project(upstream, project_id, request) -> SaveResult`: compute `mine` = `base` overlaid with `changes`; reject with a validation error if `mine.key_dates` differs from `base.key_dates` and has two entries with the same `label.strip().casefold()`; read the current upstream record; if `mine == base` return `Unchanged`; otherwise build the `PUT` body from the fresh record's six editable fields with the five form fields replaced by `mine` (so `linked_companies` comes from the fresh read), write it, and return `Saved(merged_with_others=False)`. This direct overlay is replaced by the merge in US3
- [X] T023 [US2] Add `PUT /api/projects/{project_id}` to `backend/app/main.py` taking `SaveRequest`, returning the save result, mapping the duplicate-label validation error to `422` and `UpstreamRejected` to `422` with the upstream's detail, so the editor sees the reason. Make T018 pass
- [X] T024 [US2] Create `frontend/src/edit.ts` with `validateForm(form, base): FormErrors` implementing the rules tested in T019 (the duplicate-label rule applies only when `form.key_dates` differs from `base.key_dates`, matching the backend). Make T019 pass
- [X] T025 [P] [US2] Create `frontend/src/components/KeyDatesEditor.tsx`: one row per key date with a label `TextField`, a `TextField type="date"`, and a remove button; an "Add key date" button; per-row error display; controlled via `value` and `onChange` props
- [X] T026 [US2] Add `SaveResult` types (`saved`, `unchanged`) to `frontend/src/types.ts` and `saveProject(id, base, changes): Promise<SaveResult>` to `frontend/src/api.ts`. The client sends the whole form as `changes`
- [X] T027 [US2] Add saving to `frontend/src/pages/ProjectEditPage.tsx`: replace the read-only key-date list with `KeyDatesEditor`; Save button disabled while saving; run `validateForm(form, base)` and show field errors without sending anything when invalid; on `saved` or `unchanged` reset `base` and `form` to the returned project and show a success notice; on any error keep the form as typed and show the reason (FR-006, FR-023)

**Checkpoint**: User Stories 1 and 2 work. Saves are still last-write-wins on the form fields.

---

## Phase 5: User Story 3 - Safe concurrent editing (Priority: P1)

**Goal**: Different-field edits by two people both survive; same-field edits are shown to the
second saver, who decides. The same holds when the other change came from the nightly import.

**Independent Test**: Two browser windows on the same project, quickstart steps 3 to 10.

### Tests for User Story 3

- [X] T028 [P] [US3] Write `backend/tests/test_merge.py` for `merge(base, mine, theirs)` covering the rule table in data-model.md for a core field (mine only, theirs only, both same value, both different → conflict with `base`/`mine`/`theirs`, `merged` holding theirs); key dates by label: different labels changed → both kept, same label changed to different dates → one conflict with `field="key_dates"` and that `label`, same label to the same date → no conflict, removed by one and changed by the other → conflict with a `null` side, both add the same label with different dates → conflict, with the same date → no conflict, a rename seen as remove plus add; label identity ignores case and surrounding spaces and a casing-only difference is not a change; reordering alone is not a change; merged list order is theirs' order with mine's additions appended; a repeated label in any of the three lists makes the whole list one field with `label=None` and list values; `theirs_changed` is true exactly when theirs differs from base
- [X] T029 [P] [US3] Extend `frontend/src/edit.test.ts` for `applyConflictChoices(merged, conflicts, choices)`: choosing "mine" on a core field sets it; on a key date sets the date, adds the entry, or removes it when mine is `null`; on a whole-list conflict replaces the list; choosing "theirs" leaves `merged` untouched

### Implementation for User Story 3

- [X] T030 [US3] Create `backend/app/merge.py`: pure `merge(base, mine, theirs) -> MergeResult(merged: EditableProject, conflicts: list[Conflict], theirs_changed: bool)` per research R3 and data-model.md, no I/O and no imports from `upstream.py` or `save.py`. Add the `Conflict` model (`field`, `label`, `base`, `mine`, `theirs`) to `backend/app/models.py`. Make T028 pass
- [X] T031 [US3] Extend `backend/tests/test_save.py` (two-editor section) using the direct upstream client as "the other writer" between loading `base` and saving: spec US3 scenarios 1 to 9, each asserting the stored upstream record and the response: different fields → `saved` with `merged_with_others: true`; same field → `409` with the conflict and the spy shows no `PUT`; `409` body has `current` equal to the stored state and `merged` with conflicting fields at theirs; re-sending with `base = current` and the chosen values stores them together with non-conflicting changes from both sides; a further change between the `409` and the re-send yields a new `409`; identical change by both → `saved`, no `PUT`; `linked_companies` changed by the other writer survives; a change injected with `after_call` between our `PUT` and the read-back → `200` `status: "changed_during_save"` with the stored project; two separate `create_app()` instances over the same upstream, each with its own http client: editor A saves through one and editor B through the other, and the different-field merge and the same-field `409` come out exactly as with a single instance (FR-018, SC-003)
- [X] T032 [US3] Update `backend/app/save.py` to the read → merge → write → read-back flow: replace the overlay with `merge(base, mine, editable(current))`; conflicts → return `Conflict` result (`status: "conflict"`, `conflicts`, `current`, `merged`) and write nothing; merge result equal to stored → no write, return `Saved` (or `Unchanged` when `mine == base`); after an acknowledged write read the record back and return `Saved(merged_with_others=theirs_changed)` if it equals what was written, else `ChangedDuringSave` (`status: "changed_during_save"`, `project`); if that read-back fails return `Saved` from the upstream's own `PUT` response. Add the two result models to `backend/app/models.py`
- [X] T033 [US3] Map the conflict result to HTTP `409` in `backend/app/main.py`. Make T031 pass
- [X] T034 [US3] Add `applyConflictChoices` to `frontend/src/edit.ts` and the `Conflict`, `conflict` and `changed_during_save` result types to `frontend/src/types.ts`; make `saveProject` in `frontend/src/api.ts` return the `409` body as a `conflict` result instead of throwing. Make T029 pass
- [X] T035 [P] [US3] Create `frontend/src/components/ConflictDialog.tsx`: lists each conflict with the field name (and key-date label), "Your value" and "Stored value" side by side (showing "removed" for `null`), a required mine/theirs choice per conflict, and Confirm (disabled until every conflict has a choice) and Cancel buttons
- [X] T036 [US3] Wire conflicts into `frontend/src/pages/ProjectEditPage.tsx`: on `conflict` open `ConflictDialog`; on Confirm build the next form with `applyConflictChoices`, set `base = current`, and save again (a further `conflict` reopens the dialog); on Cancel keep the editor's form; show "the record had changed and your save was merged" when `saved.merged_with_others` is true (FR-017) and "the record changed while you were saving" with the stored state for `changed_during_save` (FR-025)

**Checkpoint**: No lost updates in the two-editor and import scenarios (SC-001 to SC-003, SC-005).

---

## Phase 6: User Story 4 - Unreliable records system (Priority: P2)

**Goal**: A timed-out save is checked, retried once through the merge, and always ends as saved,
not saved or unconfirmed. Slow loads look like loading.

**Independent Test**: Quickstart steps 11 to 13, and the forced sequences in the backend tests.

### Tests for User Story 4

- [X] T037 [P] [US4] Extend `backend/tests/test_save.py` (timeout section) with `flaky_upstream` and `FixedRandom`: timeout and applied (`0.0, 0.0`) → `200 saved`, exactly one `PUT`; timeout and lost, then success (`0.0, 0.9, 0.5`) → `200 saved`, two `PUT`s, record stored; two lost timeouts (`0.0, 0.9, 0.0, 0.9`) → `503` `status: "not_saved"`, record unchanged, exactly two `PUT`s; lost timeout followed by a conflicting change from the other writer (`after_call`) → `409`, no second `PUT`; timeout then the read-back fails (`fail_from`) → `504` `status: "unconfirmed"`; re-sending the same request after a timeout that was applied → `200 saved` with no further `PUT`; a transport error on the `PUT` only (`fail_call` on that call, so the read-back still works) is treated like a `504` and reconciled the same way; the first read failing → `502` and no `PUT`; no scenario issues more than two `PUT`s

### Implementation for User Story 4

- [X] T038 [US4] Change `put_project` in `backend/app/upstream.py` to return a typed outcome: `Written(record)` on `200`, `Ambiguous` on upstream `504` and on any transport error or client timeout; `ProjectNotFound`, `UpstreamRejected` and `UpstreamError` (other statuses) still raise
- [X] T039 [US4] Extend `backend/app/save.py` to the bounded loop in research R5 (at most two write attempts): after an `Ambiguous` write read the record back; equal to what was sent → `Saved`; read-back fails → `Unconfirmed`; different → first attempt: take the read-back as current and go through merge again (conflicts → `Conflict`), second attempt: `NotSaved`. Add `NotSaved` (`status: "not_saved"`) and `Unconfirmed` (`status: "unconfirmed"`) to `backend/app/models.py`
- [X] T040 [US4] Map `NotSaved` → `503` and `Unconfirmed` → `504` in `backend/app/main.py`. Make T037 pass
- [X] T041 [US4] Add `not_saved` and `unconfirmed` to the result types in `frontend/src/types.ts` and return them from `saveProject` in `frontend/src/api.ts` for `503`/`504` bodies carrying a `status`
- [X] T042 [US4] Handle both in `frontend/src/pages/ProjectEditPage.tsx`: `not_saved` → warning "not saved, your edits are kept" with the Save button available; `unconfirmed` → warning "could not confirm whether the save happened" with a "Check again" button that re-sends the same `base` and form. In both cases the form is untouched. Never show success or failure for `unconfirmed` (FR-021)

**Checkpoint**: All four stories work; every timeout path ends in a definite, truthful state.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: The deliverables the brief asks for, and proof that everything runs.

- [X] T043 Run every check and fix what fails: in `backend/` `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`; in `frontend/` `pnpm test`, `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`. Record the real results
- [ ] T044 Run the manual validation in `specs/001-project-editor/quickstart.md` steps 1 to 13 against the running stack, including step 10 with two backend instances on ports 8000 and 8001. Note any step that does not behave as written
- [X] T045 Replace the root `README.md` with our own: what this is, what runs, what does not, and how to start the three processes and run the checks (from quickstart.md). Keep the fictional-data notice
- [X] T046 [P] Write `DECISIONS.md` (one page): what "the same field" means for key dates and why; base-in-request three-way merge and why not a version store; the accepted check-then-write window and what the read-back does and does not catch; the single retry and the late-applied-write assumption; what was cut (auth and identity, audit history, presence, list search and paging, frontend component tests, caching); what breaks first with 50 editors
- [X] T047 [P] Update `CLAUDE.md` with the backend and frontend commands (including a single test) and the backend's module layout and save flow, replacing the "still to be built" note
- [X] T048 [P] Write `ai-trail/README.md`: how the tooling was set up (global `CLAUDE.md`, Spec Kit, the three hooks), where the artifacts are (`.specify/`, `specs/`, `.claude/`, `ai-trail/prompts.md`), and section headings for the author's own note on approach, where the tool carried the work, where it was overridden, and what was checked by hand

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: needs Setup; blocks every story
- **US1 (Phase 3)**: needs Foundational
- **US2 (Phase 4)**: needs US1 (the edit page and the detail endpoint)
- **US3 (Phase 5)**: needs US2 (replaces the overlay inside `save.py` with the merge)
- **US4 (Phase 6)**: needs US3 (the retry re-runs the merge)
- **Polish (Phase 7)**: needs the stories being delivered

The stories build on one another because they share `save.py` and `ProjectEditPage.tsx`. Each is
still a complete, testable increment at its checkpoint.

### Within Each User Story

- Test tasks first; confirm they fail
- Backend: models → upstream client → `merge.py`/`save.py` → route
- Frontend: types and `api.ts` → `edit.ts` → components → page

### Parallel Opportunities

- Setup: T002 and T003 alongside T001
- Foundational: T005 and T006 together; T010 and T011 alongside the backend tasks
- Per story, the backend and frontend tracks touch different files and can run side by side:
  - US1: T013 with T015
  - US2: T018 with T019; T025 alongside T020–T023
  - US3: T028 with T029; T035 alongside T030–T033
  - US4: T037 alongside T041
- Polish: T046, T047 and T048 together

---

## Parallel Example: User Story 3

```bash
# Tests first, in parallel:
Task: "Write backend/tests/test_merge.py for merge(base, mine, theirs)"
Task: "Extend frontend/src/edit.test.ts for applyConflictChoices"

# Then two tracks side by side:
Task: "Create backend/app/merge.py"            # → T031 → T032 → T033
Task: "Create frontend/src/components/ConflictDialog.tsx"
```

---

## Implementation Strategy

### MVP First

1. Phase 1 and Phase 2
2. Phase 3 (US1): list and open → validate with quickstart step 1
3. Phase 4 (US2): edit and save → validate with quickstart step 2

### Incremental Delivery

4. Phase 5 (US3): the core of the brief → quickstart steps 3 to 10
5. Phase 6 (US4): timeouts → quickstart steps 11 to 13
6. Phase 7: deliverables and full verification

If time runs out, stop at a checkpoint and say so in `README.md` and `DECISIONS.md`. US3 is the
piece the brief is about; US4's frontend notices (T041, T042) are the first candidates to cut,
since the backend already returns truthful statuses.

---

## Notes

- One topic per commit, Conventional Commits; nothing is pushed without confirmation
- The ruff hook formats every edited `.py` and reports lint errors it cannot fix
- Three things in the plan are still untested and may need adjusting in T001 and T009:
  `uv run --env-file`, the `../upstream` path dependency, and `httpx.ASGITransport` under FastAPI's
  `TestClient`
- Requirement coverage: FR-001–003 → US1; FR-004–008 → US2; FR-009–018, FR-025 → US3;
  FR-019 → US1 and US2 pages; FR-020–022 → US4; FR-023 → US2 and US4; FR-024 → T002, T004, T005, T013
