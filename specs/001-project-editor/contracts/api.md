# API Contract: backend ↔ browser

The only interface this feature exposes. All paths are under `/api`. Bodies are JSON. Shapes are
defined in [../data-model.md](../data-model.md). The browser never sees the upstream URL or key.

## GET /api/projects

Lists every project.

| Status | Body | When |
|---|---|---|
| `200` | `ProjectSummary[]` | always, in upstream order |
| `502` | `{ "detail": string }` | upstream unreachable, answered with an error, or returned a record that does not validate |

## GET /api/projects/{id}

One project, reduced to what the form needs.

| Status | Body | When |
|---|---|---|
| `200` | `ProjectDetail` | found |
| `404` | `{ "detail": string }` | unknown id |
| `502` | `{ "detail": string }` | upstream unreachable, answered with an error, or returned a record that does not validate |

May take about 2 seconds; the backend waits for it.

## PUT /api/projects/{id}

Saves an edit. Request body: `SaveRequest`.

```json
{
  "base": {
    "name": "Cerro Talvi Solar Park",
    "sector": "energy",
    "country": "Chile",
    "stage": "tender",
    "key_dates": [{ "label": "Tender launch", "date": "2026-03-01" }]
  },
  "changes": {
    "stage": "financing",
    "key_dates": [{ "label": "Tender launch", "date": "2026-04-15" }]
  }
}
```

| Status | `status` in body | Body | Written? |
|---|---|---|---|
| `200` | `saved` | `{ status, project, merged_with_others }` | yes, or already stored |
| `200` | `unchanged` | `{ status, project }` | no |
| `200` | `changed_during_save` | `{ status, project }` | yes, then changed by someone else |
| `409` | `conflict` | `{ status, conflicts, current, merged }` | no |
| `503` | `not_saved` | `{ status }` | no |
| `504` | `unconfirmed` | `{ status }` | unknown |
| `404` | — | `{ "detail": string }` | no |
| `422` | — | `{ "detail": [...] }` (FastAPI validation errors) | no |
| `502` | — | `{ "detail": string }` | no — the first read failed or returned a record that does not validate |

`409` example:

```json
{
  "status": "conflict",
  "conflicts": [
    { "field": "stage", "label": null,
      "base": "tender", "mine": "financing", "theirs": "construction" },
    { "field": "key_dates", "label": "Tender launch",
      "base": "2026-03-01", "mine": "2026-04-15", "theirs": null }
  ],
  "current": { "name": "…", "sector": "energy", "country": "Chile", "stage": "construction",
               "key_dates": [] },
  "merged":  { "name": "…", "sector": "energy", "country": "Chile", "stage": "construction",
               "key_dates": [] }
}
```

### Rules the client relies on

- **Idempotent re-send**: sending the same request again is always safe. If the earlier attempt
  did land, the answer is `saved` and nothing is written twice. This is how "check again" works
  after `unconfirmed`, and how "save again" works after `not_saved`.
- **Resolving a conflict**: send a new request with `base` = the `409`'s `current`, and `changes` =
  the `409`'s `merged` with the editor's value applied for each conflict they resolved as "mine".
  The request is checked from scratch; a further `409` is possible.
- **`422` cases**: malformed body; empty `name` or `country`; unknown `sector` or `stage`; a key
  date with an empty label or invalid date; two key dates with the same label (ignoring case and
  surrounding spaces) in a list that differs from `base`; or the upstream itself rejected the write
  as invalid, in which case `detail` is the upstream's.
- **`merged_with_others: true`** on `saved` means the stored record contains changes the editor did not make
  and had not seen; the client shows a notice (FR-017).

## Upstream calls made per request (for reference)

| Our endpoint | Upstream calls |
|---|---|
| `GET /api/projects` | 1 × `GET /projects` |
| `GET /api/projects/{id}` | 1 × `GET /projects/{id}` |
| `PUT /api/projects/{id}` | 1–3 × `GET /projects/{id}`, 0–2 × `PUT /projects/{id}` |
