from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

Sector = Literal["energy", "mining", "water", "transport", "oil_and_gas", "ict"]
Stage = Literal[
    "idea", "feasibility", "tender", "financing", "construction", "operation", "cancelled"
]
FieldName = Literal["name", "sector", "country", "stage", "key_dates"]


class KeyDate(BaseModel):
    label: str
    date: date


class ProjectSummary(BaseModel):
    id: str
    name: str
    sector: Sector
    country: str
    stage: Stage


class EditableProject(BaseModel):
    """The five fields the edit form shows. Also the shape of `base` in a save."""

    name: str
    sector: Sector
    country: str
    stage: Stage
    key_dates: list[KeyDate]


class ProjectDetail(EditableProject):
    id: str


class UpstreamRecord(ProjectDetail):
    """What we require of a record the upstream returns. Other fields are ignored."""

    linked_companies: list[dict[str, Any]]


class ProjectChanges(BaseModel):
    """Fields that are omitted, or equal to `base`, are unchanged."""

    name: str | None = None
    sector: Sector | None = None
    country: str | None = None
    stage: Stage | None = None
    key_dates: list[KeyDate] | None = None


class SaveRequest(BaseModel):
    base: EditableProject
    changes: ProjectChanges


ConflictValue = str | list[KeyDate] | None


class Conflict(BaseModel):
    """One field changed by both sides to different values.

    For a single key date `label` is set and the values are ISO dates, or None when that side
    has no such key date. For a whole-list conflict `label` is None and the values are lists.
    """

    field: FieldName
    label: str | None
    base: ConflictValue
    mine: ConflictValue
    theirs: ConflictValue


class Saved(BaseModel):
    status: Literal["saved"] = "saved"
    project: ProjectDetail
    merged_with_others: bool


class Unchanged(BaseModel):
    status: Literal["unchanged"] = "unchanged"
    project: ProjectDetail


class ChangedDuringSave(BaseModel):
    status: Literal["changed_during_save"] = "changed_during_save"
    project: ProjectDetail


class Conflicted(BaseModel):
    status: Literal["conflict"] = "conflict"
    conflicts: list[Conflict]
    current: EditableProject
    merged: EditableProject


class NotSaved(BaseModel):
    status: Literal["not_saved"] = "not_saved"


class Unconfirmed(BaseModel):
    status: Literal["unconfirmed"] = "unconfirmed"


SaveResult = Saved | Unchanged | ChangedDuringSave | Conflicted | NotSaved | Unconfirmed
