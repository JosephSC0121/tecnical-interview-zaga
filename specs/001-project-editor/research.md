# Research: Project Editor

Phase 0 output for [plan.md](plan.md). Each entry is a decision the plan depends on. There were no
open `NEEDS CLARIFICATION` items; the stack and the outline of the API were given as input.

## R1. Where conflict detection state lives

- **Decision**: The browser sends `base` (the edit DTO it loaded) with every save. The backend
  re-reads the upstream record (`theirs`) and runs a three-way merge of `base`, `mine` and `theirs`.
  The backend stores nothing between requests.
- **Rationale**: The upstream has no version, etag or timestamp, so there is nothing to do a
  conditional write against. Keeping the base on the client is the only place that works for three
  instances with no shared store, and comparing against a fresh upstream read is what makes the
  nightly import look exactly like another editor (Constitution II, FR-018).
- **Alternatives considered**:
  - *Server-side version counter or content hash per record, in memory*: wrong on two of three
    instances and blind to the nightly import.
  - *Shared store (Redis, database) for versions or locks*: closes the gap between editors only,
    not against the import; adds infrastructure. Rejected in clarification (Q2).
  - *Content hash sent as an ETag (`If-Match`)*: detects "something changed" but not *which
    field*, so it cannot merge different-field edits. It would force a conflict on every
    concurrent save.

## R2. Shape of the save request and the conflict response

- **Decision**: `PUT /api/projects/{id}` takes `{base, changes}`. `changes` is a partial edit DTO;
  a field that is omitted or equal to `base` is unchanged, so a client may send the whole form.
  The backend computes `mine = base` overlaid with `changes`. A conflict answers `409` with
  `conflicts: [{field, label, base, mine, theirs}]` plus two extra members: `current` (the record
  as stored now) and `merged` (the merge result with every conflicting field left at `theirs`).
- **Rationale**: The two extra members let the browser resolve a conflict without re-implementing
  the merge. It starts from `merged`, applies the editor's value for each conflict where they chose
  "mine", and saves again with `base = current`. Because the new base is the state the editor
  actually looked at, the backend's ordinary merge re-checks it for free: if the record changed
  again, new conflicts appear (FR-013, User Story 3 scenario 9). No "resolution" concept exists
  on the server.
- **Alternatives considered**:
  - *Send `resolutions: {field: mine|theirs}` with the retry*: a resolution is only valid against
    the `theirs` the editor saw, so each one would have to carry that value too. More contract,
    more server logic, same guarantee.
  - *`409` with only `conflicts`* (the outline as given): the browser would need its own copy of
    the key-date merge to rebuild the list. Two implementations of the riskiest logic.

## R3. Merge rules

- **Decision**: A pure function `merge(base, mine, theirs) -> MergeResult(merged, conflicts,
  theirs_changed)` in `backend/app/merge.py`. Fields are `name`, `sector`, `country`, `stage`, and
  one field per key date keyed by its label after `strip()` and `casefold()`; the value of a
  key-date field is its date, or absent. Per field: if mine differs from base and theirs differs
  from base and they differ from each other, it is a conflict; otherwise the result is mine if
  mine changed, else theirs. If any of the three lists has a repeated normalised label, the whole
  list is one field compared as a set of `(label, date)` pairs.
- **Ordering**: the merged key-date list keeps `theirs` order, drops entries the editor removed,
  and appends entries the editor added. Order is never compared (spec Edge Cases).
- **Label casing**: a change of casing or surrounding spaces alone is not a change; the stored
  spelling is kept.
- **Rationale**: Exactly FR-009 to FR-016 as clarified. A pure function with no I/O is what makes
  the risky logic testable in isolation (Constitution V).
- **Alternatives considered**: a generic JSON three-way merge library — would treat lists by
  position, which is the option rejected in clarification (Q1), and adds a dependency.

## R4. Building the upstream `PUT` body

- **Decision**: The body is the editable fields of the freshly read upstream record, with the five
  form fields replaced by the merge result. `linked_companies` is copied from that fresh read.
- **Rationale**: The upstream `PUT` is a full replace and requires all six editable fields. Taking
  `linked_companies` from the read made inside the same save means an import that changed them
  while the form was open is preserved (FR-007, SC-005). Read-only fields are ignored by the
  upstream, so they are not sent.
- **Alternatives considered**: round-tripping `linked_companies` through the browser — widens the
  DTO for no benefit and would let a stale copy overwrite the import's.

## R5. Save algorithm, ambiguous `504`s and the single retry

- **Decision**: one bounded loop in `backend/app/save.py`, at most two write attempts:

  1. Read the record. If this fails, nothing was written: answer `502`.
  2. Merge. Conflicts → `409`. Merge result equal to what is stored → no write; answer `saved`
     (or `unchanged` if the editor changed nothing).
  3. Write. Then read the record back.
     - Read-back equals what was written → `saved`.
     - Write was acknowledged but read-back differs → `changed_during_save` (FR-025).
     - Write timed out and read-back differs → it was not applied (or was overwritten); take the
       read-back as the new current state and go to step 2 once more (FR-022).
     - Write timed out and the read-back fails → `unconfirmed` (FR-021).
     - Write was acknowledged and the read-back fails → `saved`, using the upstream's own response.
  4. A second timed-out, unapplied write → `not_saved`.

- **What counts as ambiguous**: an upstream `504`, and any transport error or client timeout on the
  `PUT` (the request may have reached the upstream). They are handled identically.
- **"Check again" for `unconfirmed`**: the browser re-sends the same `{base, changes}`. If the
  write had landed, mine and theirs are now identical for every changed field, the merge finds
  nothing to write, and the answer is `saved`. No extra endpoint is needed.
- **Rationale**: Every branch ends in exactly one of the outcomes the spec allows, and the retry
  goes through the same merge as a first attempt, so it can never overwrite a change that arrived
  in between (Constitution III).
- **Known limits, to restate in `DECISIONS.md`**:
  - The check-then-write window (clarification Q2) is the time between step 1/2 and step 3.
  - After a timeout, "the stored record equals what I sent" is taken as "my write landed". If
    someone else saved the identical values in that instant the answer is still correct for the
    editor.
  - The check assumes a timed-out write has landed or not by the time the timeout is received
    (spec Assumptions). True of this upstream; not of every gateway.
- **Alternatives considered**: retry loop with backoff (rejected in clarification Q3, option C);
  no automatic retry (option A).

## R6. Upstream client and timeouts

- **Decision**: one shared `httpx.AsyncClient` created in the FastAPI lifespan, with the
  `X-Api-Key` header set from the environment, `connect=2s` and `read=5s`. Slow reads (~2 s) are
  simply waited for; reads are not retried.
- **Rationale**: 5 s clears the documented 2 s slow path with margin, so the slow path is a
  loading state in the browser (FR-019) rather than an error. The client is a connection pool, not
  state about records, so it does not touch Constitution II.
- **Worst case**: a save makes at most 3 reads and 2 writes. With every read on the slow path that
  is about 6 s; the browser shows "saving" throughout.
- **Alternatives considered**: a short read timeout plus retries — turns a known 2 s delay into
  errors and extra load.

## R7. Configuration

- **Decision**: `UPSTREAM_BASE_URL` (default `http://127.0.0.1:8081`) and `UPSTREAM_API_KEY`
  (required, no default in code) read from the environment in `backend/app/config.py`.
  `backend/.env.example` documents both; local runs use `uv run --env-file .env`.
- **Rationale**: the key never appears in source or in the frontend bundle (Constitution I, FR-024).
  `uv` loads the env file, so no settings library is needed.
- **Alternatives considered**: `pydantic-settings` — a dependency for two variables.

## R8. Testing against the real upstream, deterministically

- **Decision**: backend tests build the upstream with `create_app(rng=FixedRandom(...))` and mount
  it under `httpx.ASGITransport`, injected into our app as its upstream client. Our own app is
  driven with FastAPI's `TestClient`. `records-api` is a dev-only path dependency
  (`[tool.uv.sources] records-api = { path = "../upstream" }`). A small `FixedRandom` lives in
  `backend/tests/conftest.py`, since the upstream's test module is not importable as a package.
- **Rationale**: the tests exercise the real upstream behaviour (full-replace `PUT`, `504` applied
  or not) with no network, no ports and no randomness (Constitution V). Nothing in `upstream/` is
  edited. `UPSTREAM_SLOW_RATE=0` in tests so that only `PUT`s draw from the generator, which keeps
  the forced sequences short and readable.
- **Simulating the other writer**: tests write to the upstream app directly, which is exactly what
  the second editor on another instance and the nightly import both look like.
- **Alternatives considered**: mocking httpx responses — would test our assumptions about the
  upstream rather than the upstream.

## R9. Frontend shape

- **Decision**: Vite + React + TypeScript (`strict`) + MUI. `react-router-dom` for two routes
  (`/` list, `/projects/:id` edit). Plain `fetch` in a small `api.ts`; no data-fetching library.
  Native date inputs via MUI `TextField type="date"`. Vite dev server proxies `/api` to the
  backend, so there is no CORS configuration and the browser only ever talks to our origin.
  The linter shipped by the Vite template (oxlint in the version used). Vitest for the one pure module (`edit.ts`: validation
  and applying conflict choices).
- **Rationale**: a URL per project is what lets two windows open the same record, which is how the
  concurrency scenarios are demonstrated. Everything else is the smallest thing that works
  (Constitution IV).
- **Dependencies justified**: `@mui/material` with `@emotion/react` and `@emotion/styled`
  (required by the brief), `react-router-dom` (deep link per project), `vitest` (dev only).
- **Cut**: client-side caching, optimistic updates, date-picker library, component tests, global
  state library. To be listed in `DECISIONS.md`.

## R10. Allowed values for sector and stage

- **Decision**: declared as `Literal` types in `backend/app/models.py` and mirrored as constants in
  `frontend/src/types.ts`.
- **Rationale**: the spec assumes the sets are fixed. The backend must not import the upstream
  package at runtime, and an endpoint just to serve two constant lists is not worth its weight.
- **Risk**: the two lists can drift from the upstream's. A backend test asserts they equal the
  upstream's `SECTORS` and `STAGES`.
