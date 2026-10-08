# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A take-home hiring challenge: an editing layer in front of an upstream records API we cannot change.
The original brief is the root `README.md` in the first commit (`git show 4fc121b:README.md`). The
code is extended live in an interview, so favour small, readable changes.

This is a Spec Kit project. `.specify/memory/constitution.md` holds five binding principles, and
`specs/001-project-editor/` holds the spec, plan, contract and tasks. The spec is the source of
truth: update it before implementing anything it does not cover.

## Hard constraints

- **Never modify anything in `upstream/`.** A PreToolUse hook blocks it. Tests may import from it.
- **The browser never calls the upstream.** It talks to `/api` only; the API key stays in the backend.
- **The backend is stateless.** Production is three instances behind a load balancer plus a nightly
  import that writes to the upstream directly. No correctness may depend on in-process memory, a
  cache or a lock; anything remembered about a record can be stale.
- **No silent overwrites.** A same-field conflict always goes to the person saving second.

## Commands

```sh
# Upstream (rates at 0 = deterministic)
cd upstream && UPSTREAM_SLOW_RATE=0 UPSTREAM_TIMEOUT_RATE=0 uv run upstream     # :8081

# Backend
cd backend && uv run --env-file .env uvicorn app.main:create_app --factory --port 8000
cd backend && uv run pytest                                  # no servers needed
cd backend && uv run pytest tests/test_save.py::TestTwoEditors::test_different_fields_both_survive
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pyright

# Frontend
cd frontend && pnpm dev                                      # :5173, proxies /api to :8000
cd frontend && pnpm test && pnpm lint && pnpm exec tsc -b && pnpm build
cd frontend && pnpm exec vitest run -t "removes a key date"
```

`backend/.env` is a copy of `backend/.env.example`. `.claude/launch.json` starts all three servers
for the preview pane.

## Backend (`backend/app/`)

The save path is the heart of the project and spans three modules:

- `merge.py` — pure three-way merge of `base` (what the editor loaded), `mine` (what they sent) and
  `theirs` (what is stored now). Fields are `name`, `sector`, `country`, `stage`, and one field per
  key date keyed by `label.strip().casefold()`. If any list has a repeated label, the whole list is
  one field. `same_content` is the equality used everywhere: it ignores key-date order and label
  spelling.
- `save.py` — `save_project`: read the record → merge → on conflict return it and write nothing →
  write a body built from the *fresh* record plus the merged form fields (this is what preserves
  `linked_companies`) → read back. An ambiguous write (`504` or transport error) is checked by that
  read-back and retried once through the merge; at most two writes per request.
- `upstream.py` — the only module that calls the upstream. Validates every record it returns and
  turns failures into `ProjectNotFound`, `UpstreamError` (→ 502), `UpstreamRejected` (→ 422), or an
  `Ambiguous` write outcome.

`main.py` is the app factory, the three routes and the status mapping: `saved`, `unchanged` and
`changed_during_save` are 200, `conflict` 409, `not_saved` 503, `unconfirmed` 504. The contract is
`specs/001-project-editor/contracts/api.md`.

Validation of an edit lives in `save.py`, not in the pydantic models, because it applies only to
what the editor changed: a record that is already odd upstream must stay editable.

### Tests

`tests/harness.py` runs the real upstream app in-process behind `UpstreamSpy`, an httpx transport
that counts our calls and can fail one (`fail_call`), fail from one on (`fail_from`), answer one
with a canned response (`respond_call`) or run a callback after one (`after_call`). `Upstream.write`
plays the other writer by saving straight to the upstream. Timeouts are forced with
`flaky_upstream(TIMEOUT, LOST, ...)`: each upstream `PUT` draws one value (timeout if < 0.1) and,
on a timeout, a second (applied if < 0.5).

## Frontend (`frontend/src/`)

- `edit.ts` — all non-visual logic: `validateForm` and `applyConflictChoices`. The only tested module.
- `api.ts` — `saveProject` returns the `SaveResult` union for any response that carries a `status`,
  whatever the HTTP code; only real failures throw `ApiError`.
- `pages/ProjectEditPage.tsx` — holds `base` and `form`. After a `409` it applies the choices to the
  returned `merged`, sets `base` to the returned `current`, and saves again, so the backend
  re-checks from scratch.

Allowed sectors and stages are duplicated in `types.ts` and `backend/app/models.py`; a backend test
pins the backend's against the upstream's.

## Hooks (`.claude/hooks/`)

- `block-upstream.sh` denies edits and write-looking shell commands under `upstream/`.
- `ruff-python.sh` formats and lints every edited `.py` and reports what it cannot fix.
- `log-prompt.sh` appends every prompt to `ai-trail/prompts.md`.
