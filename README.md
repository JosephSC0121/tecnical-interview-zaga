# Project editor

An editing layer in front of an upstream records API that we do not own and cannot change. Two
people can edit the same project at once: changes to different fields are merged, and a change to
the same field is shown to whoever saves second, who decides. The original brief for this challenge
is in the first commit of this repository.

- `upstream/` — the records API, owned by another team. Untouched.
- `backend/` — FastAPI. The only thing that talks to the upstream.
- `frontend/` — React + MUI. Talks only to the backend.

Why it is built this way is in [DECISIONS.md](DECISIONS.md). How it was built with AI tooling is in
[ai-trail/](ai-trail/README.md).

## Run it

Needs [uv](https://docs.astral.sh/uv/) and Node.js with pnpm. Three terminals:

```sh
# 1. Upstream. The two variables switch off its random slowness and timeouts.
cd upstream
UPSTREAM_SLOW_RATE=0 UPSTREAM_TIMEOUT_RATE=0 uv run upstream          # http://127.0.0.1:8081

# 2. Backend
cd backend
cp .env.example .env                                                   # first time only
uv run --env-file .env uvicorn app.main:create_app --factory --port 8000

# 3. Frontend
cd frontend
pnpm install                                                           # first time only
pnpm dev                                                               # http://localhost:5173
```

Open http://localhost:5173. To see the concurrency behaviour, open the same project in two windows.
Restarting the upstream resets its data.

Drop the two `UPSTREAM_*` variables to get the upstream's real behaviour: about one project load in
ten takes 2 seconds and about one save in ten times out.

## Checks

```sh
cd backend
uv run pytest                              # 66 tests; no servers needed
uv run pytest tests/test_merge.py -k rename
uv run ruff check . && uv run ruff format --check .
uv run pyright

cd frontend
pnpm test                                  # 12 tests
pnpm lint
pnpm exec tsc -b
pnpm build
```

## What runs

- **List**: all projects with id, name, sector, country and stage.
- **Edit**: name, sector, country, stage and key dates (add, change, remove). Linked companies and
  every other field of the record pass through each save untouched.
- **Concurrent edits**: different fields are merged; the same field opens a dialog with your value
  and the stored value, and nothing is written until you choose. A key date is a field of its own,
  identified by its label. This holds across backend instances and when the other change was
  written straight to the upstream.
- **Timeouts**: a save that times out is checked against the record and retried once. It ends as
  saved, not saved, or "could not confirm", and what the screen says matches what is stored.

## What does not

- **Two saves that overlap within a few milliseconds** on the same project can still lose one
  update without anyone being told. The upstream has no conditional write, so this cannot be closed
  from here. See DECISIONS.md.
- **No sign-in.** A conflict says "someone else", not who.
- **No history, no live presence**, no search or paging in the list.
- **The "not saved" and "could not confirm" messages in the UI** are covered by backend tests and by
  a scripted run against a flaky upstream, but I have not seen them in the browser.
- **The frontend has tests only for its pure logic** (`src/edit.ts`). Components are not tested.

All projects, companies and places in this repository are fictional.
