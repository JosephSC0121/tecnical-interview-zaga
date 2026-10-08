"""Three-way merge of one editor's changes onto the record as it is stored now.

Pure: no I/O. `base` is what the editor loaded, `mine` what they submitted, `theirs` what the
upstream holds at the moment of saving. A field is a core field, or one key date identified by
its label; when a label repeats the whole key-date list is treated as a single field.
"""

from dataclasses import dataclass
from datetime import date

from app.models import Conflict, EditableProject, KeyDate

CORE_FIELDS = ("name", "sector", "country", "stage")


@dataclass(frozen=True)
class MergeResult:
    merged: EditableProject
    conflicts: list[Conflict]
    theirs_changed: bool


def merge(base: EditableProject, mine: EditableProject, theirs: EditableProject) -> MergeResult:
    conflicts: list[Conflict] = []
    core: dict[str, str] = {}
    for field in CORE_FIELDS:
        b, m, t = getattr(base, field), getattr(mine, field), getattr(theirs, field)
        if _is_conflict(b, m, t):
            conflicts.append(Conflict(field=field, label=None, base=b, mine=m, theirs=t))
        core[field] = m if _mine_wins(b, m, t) else t

    lists = (base.key_dates, mine.key_dates, theirs.key_dates)
    if any(_has_repeated_label(key_dates) for key_dates in lists):
        key_dates, key_date_conflicts = _merge_whole_list(*lists)
    else:
        key_dates, key_date_conflicts = _merge_by_label(*lists)

    return MergeResult(
        merged=EditableProject.model_validate(core | {"key_dates": key_dates}),
        conflicts=conflicts + key_date_conflicts,
        theirs_changed=not same_content(base, theirs),
    )


def same_content(a: EditableProject, b: EditableProject) -> bool:
    """Equality that ignores what is not a field: key-date order and label spelling."""
    return all(getattr(a, f) == getattr(b, f) for f in CORE_FIELDS) and _as_set(
        a.key_dates
    ) == _as_set(b.key_dates)


def label_key(label: str) -> str:
    return label.strip().casefold()


def _is_conflict(base: object, mine: object, theirs: object) -> bool:
    return mine != base and theirs != base and mine != theirs


def _mine_wins(base: object, mine: object, theirs: object) -> bool:
    return mine != base and theirs == base


def _has_repeated_label(key_dates: list[KeyDate]) -> bool:
    keys = [label_key(key_date.label) for key_date in key_dates]
    return len(set(keys)) != len(keys)


def _as_set(key_dates: list[KeyDate]) -> frozenset[tuple[str, date]]:
    return frozenset((label_key(key_date.label), key_date.date) for key_date in key_dates)


def _merge_by_label(
    base: list[KeyDate], mine: list[KeyDate], theirs: list[KeyDate]
) -> tuple[list[KeyDate], list[Conflict]]:
    b, m, t = (
        {label_key(key_date.label): key_date for key_date in key_dates}
        for key_dates in (base, mine, theirs)
    )
    conflicts: list[Conflict] = []
    mine_won: dict[str, KeyDate | None] = {}
    for key in dict.fromkeys([*t, *m, *b]):
        base_date, my_date, their_date = (_date_of(side.get(key)) for side in (b, m, t))
        if _is_conflict(base_date, my_date, their_date):
            shown = m.get(key) or t.get(key) or b[key]
            conflicts.append(
                Conflict(
                    field="key_dates",
                    label=shown.label,
                    base=_iso(base_date),
                    mine=_iso(my_date),
                    theirs=_iso(their_date),
                )
            )
        elif _mine_wins(base_date, my_date, their_date):
            mine_won[key] = m.get(key)

    merged: list[KeyDate] = []
    for key_date in theirs:
        key = label_key(key_date.label)
        if key not in mine_won:
            merged.append(key_date)
        elif (winner := mine_won[key]) is not None:
            merged.append(winner)
    merged += [
        kd for kd in mine if label_key(kd.label) in mine_won and label_key(kd.label) not in t
    ]
    return merged, conflicts


def _merge_whole_list(
    base: list[KeyDate], mine: list[KeyDate], theirs: list[KeyDate]
) -> tuple[list[KeyDate], list[Conflict]]:
    b, m, t = _as_set(base), _as_set(mine), _as_set(theirs)
    if _is_conflict(b, m, t):
        conflict = Conflict(field="key_dates", label=None, base=base, mine=mine, theirs=theirs)
        return theirs, [conflict]
    return (mine if _mine_wins(b, m, t) else theirs), []


def _date_of(key_date: KeyDate | None) -> date | None:
    return key_date.date if key_date else None


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None
