# Prompt log

Every prompt sent to Claude Code in this repository, appended by `.claude/hooks/log-prompt.sh`.


## 2026-10-08 01:04:38 UTC · session 37dd4af8

`````text
/init
`````

## 2026-10-08 01:22:47 UTC · session 37dd4af8

`````text
specify init
`````

## 2026-10-08 01:46:34 UTC · session 37dd4af8

`````text
/speckit-constitution I. Upstream is untouchable: never modify upstream/; the browser never calls it directly.
II. Stateless backend: no correctness may depend on in-process memory, caches or locks
    (3 instances behind a LB; a nightly job writes to upstream directly, so anything we
    remember about a record can be stale). Always re-read upstream before deciding a write.
III. No silent overwrites: a same-field conflict is always surfaced to the second saver.
IV. Honest scope: small, readable, works end-to-end; cuts are documented in DECISIONS.md.
V. Tests pin behaviour, not coverage: pytest for merge/conflict logic and 504 handling,
   using upstream create_app(rng=...) with FixedRandom for slow/timeout paths.
Stack: Python + FastAPI + httpx backend; React + MUI + Vite frontend; uv / pnpm.
`````

## 2026-10-08 02:17:11 UTC · session 37dd4af8

`````text
/speckit-specify Project editor for a research team, in front of an upstream records API
we cannot change.

P1 – List projects: an editor sees all projects (id, name, sector, country, stage) and opens one.
P1 – Edit a project: edit name, sector, country, stage and key dates (add/edit/remove), then save.
     Fields not shown in the form (e.g. linked companies) must survive every save intact.
P1 – Safe concurrent editing: two editors open the same project. If they change different
     fields, both changes survive. If they change the same field, the second saver is shown
     their value vs. the current value and decides; nothing is resolved silently. This must
     also hold when the record was changed by the nightly import, not by another editor.
P2 – Unreliable upstream: slow reads show a loading state; an ambiguous save (gateway timeout)
     is never reported as success or failure without checking the record's actual state.
P3 – (cut candidates) auth/user identity, audit history, real-time presence.

Success: no lost updates in the two-editor scenarios; a timed-out save ends in a definite
state; linked companies are never dropped.
`````

## 2026-10-08 02:21:10 UTC · session 37dd4af8

`````text
/speckit-clarify
`````

## 2026-10-08 02:37:03 UTC · session 37dd4af8

`````text
Each key date is a field, identified by its label (case- and whitespace-insensitive). Renaming a label is equivalent to deleting one field and adding another. If a project has duplicate labels, the entire list is treated as a single field. That is what the spec says today.
`````

## 2026-10-08 02:40:03 UTC · session 37dd4af8

`````text
Accept the gap, keep it as short as possible and document it in `DECISIONS.md`. After every write the record is read back and, if it does not match what was written, the editor is told. No new infrastructure.
`````

## 2026-10-08 02:44:52 UTC · session 37dd4af8

`````text
Did you read the readme inside the upstream folder?
`````

## 2026-10-08 02:48:00 UTC · session 37dd4af8

`````text
Option B: One automatic retry, re-evaluating the save against the current state first. If it times out again and is still not applied, the editor is told "not saved".
`````

## 2026-10-08 02:50:01 UTC · session 37dd4af8

`````text
Option A: An explicit third outcome, "unconfirmed": the edits are kept in the form and the editor can check again. This is what the spec says today.
`````

## 2026-10-08 02:53:55 UTC · session 37dd4af8

`````text
/speckit-plan FastAPI backend in backend/ with an httpx client to upstream (API key from env,
timeouts tuned for the ~2s slow reads). Endpoints: GET /api/projects (slim list DTO),
GET /api/projects/{id} (edit DTO: core fields + key_dates only), PUT /api/projects/{id}
with {base, changes} → 200 merged record | 409 {conflicts:[{field, base, mine, theirs}]}.
Merge logic as a pure function in merge.py, unit-tested in isolation. On every save re-read
upstream and send a full PUT built from current upstream record + merged fields, so
linked_companies and unknown fields are preserved. 504: re-read and reconcile.
Frontend in frontend/: Vite + React + MUI, list page + edit page + conflict dialog.
No database, no cache, no locks.
`````

## 2026-10-08 03:01:07 UTC · session 37dd4af8

`````text
Create three hooks 
Block upstream/ Event PreTool use. -> for never modify upstream
Register Prompts UserPromptSubmit -> an ai-trail.prompts.ml as my trail 
Format and Lint PostToolUse run ruff every edition of a .py.
`````

## 2026-10-08 03:07:20 UTC · session 37dd4af8

`````text
/speckit-analyze
`````

## 2026-10-08 03:08:39 UTC · session 37dd4af8

`````text
/speckit-tasks
`````

## 2026-10-08 03:11:13 UTC · session 37dd4af8

`````text
/speckit-analyze
`````

## 2026-10-08 03:21:43 UTC · session 37dd4af8

`````text
For now apply F1, U2, U3, T1
`````

## 2026-10-08 03:26:24 UTC · session 37dd4af8

`````text
Rename one something like merge_with_others
the 200 is enough as the confirmation.
Add to t031 a case with tow create_app()
`````

## 2026-10-08 03:27:25 UTC · session 37dd4af8

`````text
/speckit-implement
`````

## 2026-10-08 03:58:39 UTC · session 37dd4af8

`````text
commit the prompts and merge into main
`````
