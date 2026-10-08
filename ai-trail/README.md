# AI trail

How this project was built with Claude Code.

## Setup

| Piece | Where | What it does |
|---|---|---|
| Global preferences | `~/.claude/CLAUDE.md` (not in this repo) | Plan before non-trivial changes, spec as source of truth, TDD, real check results |
| Repo guidance | [`CLAUDE.md`](../CLAUDE.md) | Constraints, commands and architecture for any future session |
| Spec Kit | [`.specify/`](../.specify/), [`.claude/skills/`](../.claude/skills/) | `specify init`, then constitution → specify → clarify → plan → tasks → analyze → implement |
| Constitution | [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) | Five principles I wrote; the tool expanded them |
| Hooks | [`.claude/settings.json`](../.claude/settings.json), [`.claude/hooks/`](../.claude/hooks/) | Block edits to `upstream/`; run ruff on every edited `.py`; log every prompt |
| Preview servers | [`.claude/launch.json`](../.claude/launch.json) | Starts upstream, backend and frontend |

## What it left behind

- [`prompts.md`](prompts.md) — every prompt of the session. Those sent before the logging hook was
  installed were reconstructed from the session transcript, with the same text and timestamps.
- [`specs/001-project-editor/`](../specs/001-project-editor/) — `spec.md` (with the clarification
  session), `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`, `quickstart.md`,
  `tasks.md`.

## Approach before any code

- Had the tool read the brief and the upstream (README, code, tests) and write `CLAUDE.md` first.
- Wrote the five principles of the constitution myself before asking for a spec.
- Wrote the user stories and success criteria myself; the tool turned them into a spec.
- Used `/speckit-clarify` to settle four decisions before planning: what "the same field" means for
  key dates, whether to accept the check-then-write window, automatic retry after a timeout, and
  the "unconfirmed" outcome.
- Gave the plan its shape myself: endpoints, `{base, changes}`, a pure `merge.py`, full `PUT` built
  from the fresh record, no database, cache or locks.
- Create three hooks 
  Block upstream/ Event PreTool use. -> for never modify upstream
  Register Prompts UserPromptSubmit -> an ai-trail.prompts.ml as my trail 
  Format and Lint PostToolUse run ruff every edition of a .py.

## Where the tool carried the work 

- The spec's acceptance scenarios and edge cases, and the research notes with rejected alternatives.
- The merge algorithm 22 tests; the save loop and its timeout tests.
- The test harness that runs the real upstream in-process with forced random draws.
- All of the frontend.
- `/speckit-analyze`, which found seven medium issues across spec, plan and tasks before any code.

## Where I overrode it 

- Asked whether it had actually read the upstream README before accepting a recommendation.
- Chose which analysis findings to apply and in what order; decided that the upstream's `200` is
  enough confirmation when the read-back fails; asked for the rename to `merged_with_others`; asked
  for the two-instance test.
- I change some styles in the frontend. 

## What I checked by hand

- Reviewed the code myself.
- Did a dependency review and a code review before running anything, for security reasons in my
  environment.
- Ran the project.
- Backend: 66 pytest tests, ruff, pyright.
- Frontend: 12 Vitest tests, oxlint, `tsc -b`, production build.
- In the browser: list of 30 projects; open a project; a same-field conflict caused by a direct
  write to the upstream, resolved in the dialog, with the stored record checked afterwards; form
  validation; a save with no changes.
- Scripted against real servers: two backend instances over one upstream; six saves against an
  upstream where every save times out, comparing each answer with the stored record.
- Not seen in the browser: the "not saved" and "could not confirm" messages.

## Deviations from the task list

- `save.py` was written directly in its final, merge-based form; the intermediate last-write-wins
  version planned for User Story 2 (T022) was skipped.
- The test helpers live in `backend/tests/harness.py`, with only fixtures in `conftest.py`.
- Field validation of an edit is in `save.py` rather than in the pydantic models, so it applies
  only to what the editor changed.
- The Vite template now ships oxlint, not ESLint; the template's choice was kept.
- Tests were written before the code in each step, but the merge tests passed on their first run
  against the implementation, so they were not seen failing for the right reason.
