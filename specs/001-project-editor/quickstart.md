# Quickstart: Project Editor

How to run the feature and prove it works. Contracts are in [contracts/api.md](contracts/api.md),
shapes in [data-model.md](data-model.md).

## Prerequisites

`uv`, Node.js with `pnpm`. Three terminals.

## Run

```sh
# 1. Upstream (deterministic: no slow reads, no timeouts)
cd upstream
UPSTREAM_SLOW_RATE=0 UPSTREAM_TIMEOUT_RATE=0 uv run upstream      # http://127.0.0.1:8081

# 2. Backend
cd backend
cp .env.example .env                                               # first time only
uv run --env-file .env uvicorn app.main:create_app --factory --port 8000

# 3. Frontend
cd frontend
pnpm install                                                       # first time only
pnpm dev                                                           # http://localhost:5173
```

Restarting the upstream resets all data to the seed.

## Automated checks

```sh
cd backend
uv run pytest                 # merge rules, save algorithm, 504 paths, API
uv run ruff check . && uv run ruff format --check .
uv run pyright

cd frontend
pnpm test                     # edit.ts: validation, applying conflict choices
pnpm lint
pnpm exec tsc --noEmit
```

Expected: all pass. The backend suite needs no running services; it mounts the upstream in-process.

## Manual validation

Open `http://localhost:5173` in two browser windows, A and B. To play the nightly import, write to
the upstream directly:

```sh
curl -s -H 'X-Api-Key: local-dev-key' http://127.0.0.1:8081/projects/P-1001
```

and `PUT` the six editable fields back with one of them changed.

| # | Steps | Expected |
|---|---|---|
| 1 | Open the list | 30 projects with id, name, sector, country, stage |
| 2 | Open P-1001, change name and one key date, add a key date, remove one, save | Saved; reload shows the same; `linked_companies` in the upstream record unchanged |
| 3 | A and B open P-1001. A changes name, saves. B changes country, saves | B is told the record was merged; stored record has both |
| 4 | A and B open P-1001. A sets stage to X, saves. B sets stage to Y, saves | B sees a conflict dialog: mine Y, stored X. Nothing written until B chooses |
| 5 | In 4, B also changed country. B picks "mine" for stage and confirms | Stored: B's stage, B's country |
| 6 | A changes one key date's date, B changes a different key date's date | Both stored, no conflict |
| 7 | A and B change the same key date to different dates | Conflict on that key date only |
| 8 | A removes a key date; B changes its date | Conflict on that key date |
| 9 | B opens P-1001. Change stage via `curl` to the upstream. B changes name, saves | Both stored. Repeat with B also changing stage: conflict |
| 10 | Stop the backend, start two on ports 8000 and 8001, send A's save to one and B's to the other (`curl`) | Same outcomes as 3 and 4 |

### Unreliable upstream

Restart the upstream with the flaky paths on, then save repeatedly:

```sh
UPSTREAM_SLOW_RATE=1 UPSTREAM_TIMEOUT_RATE=0 uv run upstream     # every project load takes ~2 s
UPSTREAM_SLOW_RATE=0 UPSTREAM_TIMEOUT_RATE=1 uv run upstream     # every save times out
```

| # | Setup | Expected |
|---|---|---|
| 11 | Slow rate 1, open a project | Loading state for ~2 s, then the form |
| 12 | Timeout rate 1, save a change several times | Each save ends as "saved" (it landed on the first or second attempt) or "not saved" with edits kept. What the UI says always matches the upstream record |
| 13 | Timeout rate 1, save, and stop the upstream while the request is in flight | "Unconfirmed", edits kept. Restart is not useful here (data resets); the exact path is covered by the automated tests |

The forced sequences (timeout-and-applied, timeout-and-lost, two timeouts in a row) are pinned in
`backend/tests/` with a fixed random generator, which is the reliable way to see each branch.
