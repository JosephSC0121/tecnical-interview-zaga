# Decisions

## What I chose

**The browser carries the base; the backend keeps nothing.** Every save sends `base` (the record as
the editor loaded it) and `changes`. The backend re-reads the record from the upstream and runs a
three-way merge of base, mine and theirs. There is no version table, cache or lock, because none of
them would be right: an in-process one is wrong on two of three instances, and any of them is blind
to the nightly import. Comparing against a fresh read makes the import look exactly like a second
editor, with no special case.

**"The same field" for key dates is one key date, identified by its label** (ignoring case and
surrounding spaces). The upstream gives key dates no id, and position shifts whenever anyone adds
or removes one, so the label is the only stable handle. It is also what an editor means by "the
Financial close date". Treating the whole list as one field would raise a conflict every time two
people touch different milestones, which is the normal case. The costs: renaming a label is seen as
removing one date and adding another, and a project whose labels repeat falls back to treating its
whole list as one field.

**A conflict is resolved by re-basing, not by a resolution protocol.** A `409` returns the stored
record and the merge with conflicting fields left at the stored value. The browser applies the
editor's choices and saves again with the stored record as the new base, so the backend checks it
from scratch. If the record moved again, a new conflict appears. The server has no notion of a
"resolution".

**Every write body is built from the record read inside that save**, with only the five form
fields replaced. That is why linked companies survive: the upstream `PUT` replaces whole lists, and
a copy round-tripped through the browser could be stale.

**A timed-out save is never guessed.** After a `504` (or any transport error on the write) the
backend reads the record. If it matches what was sent, the save happened. If not, it retries once,
through the merge again, so the retry cannot overwrite a change that arrived in between. If the
record cannot be read at all the answer is "unconfirmed", and re-sending the same request is safe:
it finds nothing left to write and answers "saved".

## What I cut, and why

| Cut | Why |
|---|---|
| Sign-in and identity | The upstream has one shared key and no users; conflicts say "someone else" |
| Audit history, live presence | Both need state the design deliberately does not have |
| A shared lock across instances | Would not cover the nightly import, and adds infrastructure |
| Search, filtering, paging | 30 projects |
| Component tests, client cache, date-picker library | Not where the risk is; the merge and the timeout paths are, and those have 66 tests |
| Editing linked companies | Not asked for; they only need to survive |

## Known limits

- **Check-then-write window.** Between reading the record and writing it, another write can land
  and be overwritten without notice. The upstream has no conditional write, so nothing on our side
  closes this. The window is the merge plus one request, typically milliseconds. After each write
  the backend reads the record back and warns if it differs, which catches a later write but not
  one that was overwritten.
- **Late writes.** The timeout check assumes a timed-out write has landed, or not, by the time the
  timeout arrives. True of this upstream. Behind a real gateway a write could land after the check.
- **Label casing.** The frontend compares labels with `toLowerCase`, the backend with `casefold`.
  They differ for a few non-English characters; the backend's answer is the one that counts.

## What breaks first with 50 editors

The check-then-write window. Today two saves rarely overlap; with 50 editors on a few hot projects
they will, and each overlap is a lost update that nobody is told about. That is the worst kind of
failure for this tool, and it grows with load.

Next comes upstream load: a save costs two or three upstream calls, each retry adds two more, and
the list fetches every project in full on each visit. After that, friction: more same-field
conflicts and a dialog that resolves one field at a time.

The real fix is upstream: a version or `If-Match` on `PUT`. With that, this backend's merge stays as
it is and the window closes. Without it, the fallback is a short per-project lock in a store shared
by the instances, accepting that the import still bypasses it.
