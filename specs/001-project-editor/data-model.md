# Data Model: Project Editor

Phase 1 output for [plan.md](plan.md). The tool persists nothing; these are the shapes that cross
its boundaries and the values the merge works on.

## Upstream record (consumed, not owned)

The upstream `Project` as documented in `upstream/README.md`. Relevant parts:

| Part | Fields | Treatment |
|---|---|---|
| Identity | `id` (`P-1001`…) | read-only |
| Form fields | `name`, `sector`, `country`, `stage`, `key_dates` | shown, merged, written |
| Pass-through | `linked_companies` | never shown; copied from the fresh read into every write |
| Other systems' | ~15 further fields | never shown, never sent |

## DTOs exposed by the backend

### ProjectSummary — list row

| Field | Type |
|---|---|
| `id` | string |
| `name` | string |
| `sector` | Sector |
| `country` | string |
| `stage` | Stage |

### KeyDate

| Field | Type | Rule |
|---|---|---|
| `label` | string | non-empty after trimming |
| `date` | date (`YYYY-MM-DD`) | valid calendar date |

Identity within a project: `label.strip().casefold()`. It has no id upstream.

### EditableProject — the edit form

| Field | Type | Rule on submit |
|---|---|---|
| `name` | string | non-empty |
| `sector` | Sector | one of the allowed values |
| `country` | string | non-empty |
| `stage` | Stage | one of the allowed values |
| `key_dates` | KeyDate[] | no two entries with the same identity, *if the list differs from base* |

`ProjectDetail` is `EditableProject` plus `id`; it is what `GET /api/projects/{id}` returns.

The duplicate-label rule is applied only when the editor changed the list, so that a record which
already has duplicates upstream can still have its other fields edited.

`Sector`: `energy`, `mining`, `water`, `transport`, `oil_and_gas`, `ict`.
`Stage`: `idea`, `feasibility`, `tender`, `financing`, `construction`, `operation`, `cancelled`.

### SaveRequest

| Field | Type | Meaning |
|---|---|---|
| `base` | EditableProject | the state the editor loaded, or `current` from the last `409` |
| `changes` | partial EditableProject | fields omitted or equal to `base` are unchanged |

`mine` is derived: `base` overlaid with `changes`. `base` is validated for shape only.

### Conflict

| Field | Type | Meaning |
|---|---|---|
| `field` | `name` \| `sector` \| `country` \| `stage` \| `key_dates` | which field |
| `label` | string \| null | the key date's label; null for core fields and for whole-list conflicts |
| `base` | value \| null | value the editor loaded |
| `mine` | value \| null | value the editor submitted |
| `theirs` | value \| null | value stored now |

Value type by case:

| Case | `field` | `label` | value |
|---|---|---|---|
| Core field | `name` etc. | null | string |
| One key date | `key_dates` | its label | date string, or null when the entry is absent on that side |
| Whole list (duplicate labels) | `key_dates` | null | KeyDate[] |

### SaveResult

Discriminated by `status`. HTTP codes are in [contracts/api.md](contracts/api.md).

| `status` | Extra members | Meaning |
|---|---|---|
| `saved` | `project`, `merged_with_others: bool` | stored record equals the merge result. `merged_with_others` is true when someone else's changes were kept alongside the editor's |
| `unchanged` | `project` | the editor changed nothing; nothing written |
| `changed_during_save` | `project` | write was acknowledged, but the record no longer matches it |
| `conflict` | `conflicts`, `current`, `merged` | nothing written; editor must choose |
| `not_saved` | — | write timed out twice and was not applied |
| `unconfirmed` | — | write timed out and the record could not be read |

In a `conflict`, `current` is the stored state and `merged` is the merge result with each
conflicting field left at `theirs`; both are `EditableProject`.

## Merge model (internal)

`merge(base, mine, theirs)` flattens each `EditableProject` into fields:

- four core fields, each a string;
- one field per key date, keyed by identity, valued by its date or *absent*;
- or, if any of the three lists has a repeated identity, a single field holding the whole list,
  compared as a set of `(identity, date)` pairs.

Per field, with `b`, `m`, `t` the three values:

| `m` vs `b` | `t` vs `b` | `m` vs `t` | Result |
|---|---|---|---|
| same | any | — | `t` |
| changed | same | — | `m` |
| changed | changed | same | `t` (no conflict) |
| changed | changed | different | conflict; `merged` holds `t` |

Output: `merged: EditableProject`, `conflicts: Conflict[]`, `theirs_changed: bool`.

Key-date list reconstruction: `theirs` order; entries the editor removed are dropped; an entry
whose date the editor changed is replaced in place; entries the editor added are appended in the
editor's order. The stored spelling of a label is kept unless the editor's entry wins.

## Save lifecycle

```text
            read fails
 start ───────────────────────────▶ 502 (nothing written)
   │ read ok
   ▼
 merge ── conflicts ───────────────▶ conflict
   │
   ├─ nothing to write ────────────▶ unchanged | saved
   ▼
 write ── acknowledged ─ read back ─┬─ equal ──────▶ saved
   │                                ├─ different ──▶ changed_during_save
   │                                └─ read fails ─▶ saved (from upstream's response)
   │
   └─ timed out ─ read back ────────┬─ equal ──────▶ saved
                                    ├─ read fails ─▶ unconfirmed
                                    └─ different ──▶ 1st attempt: back to merge with the read-back
                                                     2nd attempt: not_saved
```

## Edit form state (frontend)

```text
loading ─▶ editing ─▶ saving ─┬─▶ editing (saved / unchanged / changed_during_save: form reset
   │                          │            to the returned project, with a notice)
   ▼                          ├─▶ resolving (conflict dialog) ─▶ saving
 error (retry)                └─▶ editing (not_saved / unconfirmed / error: edits kept, notice)
```

In `resolving`, the next request is built as `base = current` and `changes = merged` with the
editor's value applied for each conflict where they chose "mine".
