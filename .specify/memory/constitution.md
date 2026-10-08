# Project Editor Constitution

## Core Principles

### I. Upstream Is Untouchable

- Nothing under `upstream/` MUST ever be modified. It stands in for an API owned by another team.
- The browser MUST NOT call the upstream API directly. Every browser request goes through our
  backend, and the upstream API key MUST never reach the frontend.
- The upstream's documented habits (last write wins, full-replace `PUT`, wide responses, slow
  reads, ambiguous `504`s) are fixed facts to design around, not bugs to work around by changing it.

Rationale: this is the one hard rule of the brief, and it mirrors the production reality of
consuming a service we do not own.

### II. Stateless Backend

- No correctness property MAY depend on in-process memory, caches or locks. Production runs three
  instances behind a load balancer, so any such state is invisible to two thirds of requests.
- Anything the backend remembers about a record MUST be treated as possibly stale: a nightly import
  job writes to the upstream directly, bypassing our backend.
- The backend MUST re-read the record from the upstream before deciding any write.
- In-process state is allowed only as an optimisation whose loss or staleness cannot change the
  outcome of a save.

Rationale: a design that is only correct on one instance, or only when we are the sole writer,
fails in exactly the environment the brief describes.

### III. No Silent Overwrites

- A same-field conflict MUST always be surfaced to the person saving second, who decides the
  outcome. Neither side may win silently.
- Edits by two people to different fields MUST both survive.
- What counts as "the same field" for `key_dates` MUST be defined explicitly in the spec and
  justified in `DECISIONS.md`.
- An ambiguous upstream result (a `504` on `PUT`) MUST NOT be reported as success or as failure
  without re-reading the record to find out which it was.

Rationale: the upstream gives no conflict detection, so this guarantee is the core value of the
layer we are building.

### IV. Honest Scope

- The solution MUST be small, readable and working end to end, in preference to broad and partial.
- Every cut MUST be documented in `DECISIONS.md` with its reason. Nothing may be described as
  working unless it has been run.
- The code MUST be left in a state fit for live extension: no dead code, no speculative
  abstractions, no dependency without a stated justification.

Rationale: the brief is deliberately larger than the time allows and is read for what was cut and
why; the code is extended live in the interview.

### V. Tests Pin Behaviour, Not Coverage

- pytest tests MUST exist for the merge and conflict logic and for `504` handling. Coverage
  percentage is not a goal.
- Slow and timeout paths MUST be tested deterministically by running the upstream in-process via
  `create_app(rng=...)` with a `FixedRandom`-style generator, never by relying on random rates.
- Importing from `upstream/` in our tests is permitted; editing it is not (Principle I).
- Where viable, the test for a behaviour is written before its implementation.

Rationale: the risky logic is concentrated in merging and in ambiguous writes; those are the
behaviours worth pinning.

## Technology Stack & Constraints

- Backend: Python, FastAPI, httpx for upstream calls; dependencies and commands managed with `uv`.
- Frontend: React, MUI, Vite; dependencies and commands managed with `pnpm`.
- Typed code on both sides: Python type hints throughout, TypeScript with `strict: true`.
- Secrets and environment-specific values (upstream URL, API key) come from environment variables,
  documented in `.env.example`; they are never hard-coded outside local-dev defaults.
- Input from the browser and responses from the upstream are both validated at the backend boundary.

## Development Workflow & Quality Gates

- The spec is the source of truth: nothing is implemented that is not in it. If something is
  missing, the spec is updated first.
- Changes are small and verifiable, one topic per commit, with Conventional Commits messages.
- Before any work is called done, lint, type-check and tests are run and their real results
  reported (`ruff` and `pyright` for Python; the frontend's linter and `tsc` for TypeScript).
- Required deliverables at the repository root: a `README.md` stating what runs, what does not and
  how to start it; a one-page `DECISIONS.md`; and the AI trail with a short note on approach.

## Governance

- This constitution supersedes other practices in this repository. Where `CLAUDE.md` or a spec
  conflicts with it, the constitution wins and the other document is corrected.
- Every plan and every review MUST check compliance with the five principles. A deviation is only
  acceptable if it is justified in the plan and recorded in `DECISIONS.md`.
- Amendments are made by editing this file with a version bump and an updated amendment date:
  MAJOR for removing or redefining a principle, MINOR for adding a principle or section or
  materially expanding guidance, PATCH for clarifications and wording.
- `CLAUDE.md` holds runtime development guidance (commands, upstream contract) and MUST be kept
  consistent with this document.

**Version**: 1.0.0 | **Ratified**: 2026-10-07 | **Last Amended**: 2026-10-07
