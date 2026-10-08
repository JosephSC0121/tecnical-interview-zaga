"""Saving one edit: read, merge, write, read back, and reconcile an ambiguous write.

Nothing is remembered between requests. Every decision is made against a record read from the
upstream inside this call, so it holds across instances and against writers that bypass us.
"""

from app.merge import label_key, merge, same_content
from app.models import (
    ChangedDuringSave,
    Conflicted,
    EditableProject,
    NotSaved,
    ProjectChanges,
    ProjectDetail,
    Saved,
    SaveRequest,
    SaveResult,
    Unchanged,
    Unconfirmed,
)
from app.upstream import Record, UpstreamClient, UpstreamError, Written

# The upstream PUT replaces all of these, so every write carries all of them.
UPSTREAM_EDITABLE_FIELDS = ("name", "sector", "country", "stage", "key_dates", "linked_companies")
MAX_WRITE_ATTEMPTS = 2


class InvalidEdit(Exception):
    def __init__(self, errors: list[dict[str, str]]) -> None:
        super().__init__("The edit is invalid")
        self.errors = errors


async def save_project(
    upstream: UpstreamClient, project_id: str, request: SaveRequest
) -> SaveResult:
    base = request.base
    mine = _apply(base, request.changes)
    _validate(base, mine)

    current = await upstream.get_project(project_id)
    for _ in range(MAX_WRITE_ATTEMPTS):
        theirs = EditableProject.model_validate(current)
        result = merge(base, mine, theirs)
        if result.conflicts:
            return Conflicted(conflicts=result.conflicts, current=theirs, merged=result.merged)
        if same_content(result.merged, theirs):
            project = ProjectDetail.model_validate(current)
            if same_content(mine, base):
                return Unchanged(project=project)
            return Saved(project=project, merged_with_others=result.theirs_changed)

        body = _write_body(current, result.merged)
        outcome = await upstream.put_project(project_id, body)
        acknowledged = isinstance(outcome, Written)
        try:
            stored = await upstream.get_project(project_id)
        except UpstreamError:
            if isinstance(outcome, Written):
                return _saved(outcome.record, result.theirs_changed)
            return Unconfirmed()

        if all(stored[field] == body[field] for field in UPSTREAM_EDITABLE_FIELDS):
            return _saved(stored, result.theirs_changed)
        if acknowledged:
            return ChangedDuringSave(project=ProjectDetail.model_validate(stored))
        # The write timed out and is not there: start over from what is stored now.
        current = stored
    return NotSaved()


def _apply(base: EditableProject, changes: ProjectChanges) -> EditableProject:
    updates = {
        field: value
        for field in changes.model_fields_set
        if (value := getattr(changes, field)) is not None
    }
    return base.model_copy(update=updates)


def _validate(base: EditableProject, mine: EditableProject) -> None:
    """Checks only what the editor changed, so a record that is already odd stays editable."""
    errors: list[dict[str, str]] = []
    for field in ("name", "country"):
        value = getattr(mine, field)
        if value != getattr(base, field) and not value.strip():
            errors.append({"field": field, "message": "Must not be empty"})

    if mine.key_dates != base.key_dates:
        seen: set[str] = set()
        for index, key_date in enumerate(mine.key_dates):
            key = label_key(key_date.label)
            if not key:
                errors.append({"field": f"key_dates.{index}.label", "message": "Must not be empty"})
            elif key in seen:
                errors.append(
                    {"field": f"key_dates.{index}.label", "message": "Label is used more than once"}
                )
            seen.add(key)

    if errors:
        raise InvalidEdit(errors)


def _write_body(current: Record, merged: EditableProject) -> Record:
    untouched = {field: current[field] for field in UPSTREAM_EDITABLE_FIELDS}
    return untouched | merged.model_dump(mode="json")


def _saved(record: Record, merged_with_others: bool) -> Saved:
    return Saved(
        project=ProjectDetail.model_validate(record), merged_with_others=merged_with_others
    )
