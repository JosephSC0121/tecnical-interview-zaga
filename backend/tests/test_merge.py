from typing import Any

from app.merge import merge
from app.models import EditableProject

TENDER = ("Tender launch", "2026-03-01")
CLOSE = ("Financial close", "2026-09-01")
START = ("Construction start", "2027-01-15")


def project(*key_dates: tuple[str, str], **fields: Any) -> EditableProject:
    defaults = {"name": "Solar Park", "sector": "energy", "country": "Chile", "stage": "tender"}
    listed = [{"label": label, "date": day} for label, day in key_dates]
    return EditableProject.model_validate(defaults | fields | {"key_dates": listed})


def dates(result_project: EditableProject) -> list[tuple[str, str]]:
    return [(kd.label, kd.date.isoformat()) for kd in result_project.key_dates]


BASE = project(TENDER, CLOSE)


class TestCoreFields:
    def test_only_mine_changed_takes_mine(self) -> None:
        result = merge(BASE, project(TENDER, CLOSE, name="Mine"), BASE)

        assert result.merged.name == "Mine"
        assert result.conflicts == []
        assert result.theirs_changed is False

    def test_only_theirs_changed_keeps_theirs(self) -> None:
        theirs = project(TENDER, CLOSE, stage="financing")

        result = merge(BASE, BASE, theirs)

        assert result.merged == theirs
        assert result.conflicts == []
        assert result.theirs_changed is True

    def test_different_fields_both_survive(self) -> None:
        mine = project(TENDER, CLOSE, name="Mine")
        theirs = project(TENDER, CLOSE, country="Peru")

        result = merge(BASE, mine, theirs)

        assert (result.merged.name, result.merged.country) == ("Mine", "Peru")
        assert result.conflicts == []

    def test_same_field_same_value_is_not_a_conflict(self) -> None:
        both = project(TENDER, CLOSE, stage="financing")

        result = merge(BASE, both, both)

        assert result.merged.stage == "financing"
        assert result.conflicts == []

    def test_same_field_different_values_conflicts_and_merged_holds_theirs(self) -> None:
        mine = project(TENDER, CLOSE, stage="financing", name="Mine")
        theirs = project(TENDER, CLOSE, stage="construction")

        result = merge(BASE, mine, theirs)

        [conflict] = result.conflicts
        assert conflict.model_dump() == {
            "field": "stage",
            "label": None,
            "base": "tender",
            "mine": "financing",
            "theirs": "construction",
        }
        assert result.merged.stage == "construction"
        assert result.merged.name == "Mine"


class TestKeyDates:
    def test_different_key_dates_changed_both_survive(self) -> None:
        mine = project(TENDER, ("Financial close", "2026-10-10"))
        theirs = project(("Tender launch", "2026-04-04"), CLOSE)

        result = merge(BASE, mine, theirs)

        assert result.conflicts == []
        assert dates(result.merged) == [
            ("Tender launch", "2026-04-04"),
            ("Financial close", "2026-10-10"),
        ]

    def test_same_key_date_to_different_dates_conflicts_on_that_date_only(self) -> None:
        mine = project(TENDER, ("Financial close", "2026-10-10"), name="Mine")
        theirs = project(TENDER, ("Financial close", "2026-11-11"))

        result = merge(BASE, mine, theirs)

        [conflict] = result.conflicts
        assert conflict.model_dump() == {
            "field": "key_dates",
            "label": "Financial close",
            "base": "2026-09-01",
            "mine": "2026-10-10",
            "theirs": "2026-11-11",
        }
        assert dates(result.merged) == [TENDER, ("Financial close", "2026-11-11")]
        assert result.merged.name == "Mine"

    def test_same_key_date_to_the_same_date_is_not_a_conflict(self) -> None:
        both = project(TENDER, ("Financial close", "2026-10-10"))

        assert merge(BASE, both, both).conflicts == []

    def test_i_remove_what_they_changed_conflicts(self) -> None:
        mine = project(TENDER)
        theirs = project(TENDER, ("Financial close", "2026-11-11"))

        [conflict] = merge(BASE, mine, theirs).conflicts

        assert (conflict.label, conflict.mine, conflict.theirs) == (
            "Financial close",
            None,
            "2026-11-11",
        )

    def test_i_change_what_they_removed_conflicts(self) -> None:
        mine = project(TENDER, ("Financial close", "2026-10-10"))
        theirs = project(TENDER)

        [conflict] = merge(BASE, mine, theirs).conflicts

        assert (conflict.base, conflict.mine, conflict.theirs) == ("2026-09-01", "2026-10-10", None)

    def test_both_remove_the_same_key_date_is_not_a_conflict(self) -> None:
        result = merge(BASE, project(TENDER), project(TENDER))

        assert result.conflicts == []
        assert dates(result.merged) == [TENDER]

    def test_both_add_the_same_label_with_different_dates_conflicts(self) -> None:
        mine = project(TENDER, CLOSE, ("Construction start", "2027-02-02"))
        theirs = project(TENDER, CLOSE, START)

        [conflict] = merge(BASE, mine, theirs).conflicts

        assert (conflict.label, conflict.base) == ("Construction start", None)

    def test_both_add_the_same_label_with_the_same_date_is_not_a_conflict(self) -> None:
        both = project(TENDER, CLOSE, START)

        result = merge(BASE, both, both)

        assert result.conflicts == []
        assert dates(result.merged) == [TENDER, CLOSE, START]

    def test_my_removal_and_my_addition_are_applied_to_their_list(self) -> None:
        mine = project(CLOSE, START)
        theirs = project(("Tender launch", "2026-03-01"), ("Financial close", "2026-11-11"))

        result = merge(BASE, mine, theirs)

        assert result.conflicts == []
        assert dates(result.merged) == [("Financial close", "2026-11-11"), START]

    def test_rename_is_a_removal_plus_an_addition(self) -> None:
        mine = project(TENDER, ("Financing closed", "2026-09-01"))
        theirs = project(TENDER, ("Financial close", "2026-11-11"))

        [conflict] = merge(BASE, mine, theirs).conflicts

        assert (conflict.label, conflict.mine, conflict.theirs) == (
            "Financial close",
            None,
            "2026-11-11",
        )

    def test_label_identity_ignores_case_and_surrounding_spaces(self) -> None:
        mine = project(TENDER, ("  financial CLOSE ", "2026-10-10"))
        theirs = project(TENDER, ("Financial close", "2026-11-11"))

        [conflict] = merge(BASE, mine, theirs).conflicts

        assert conflict.field == "key_dates"

    def test_a_casing_only_difference_is_not_a_change(self) -> None:
        mine = project(("TENDER LAUNCH", "2026-03-01"), CLOSE)

        result = merge(BASE, mine, BASE)

        assert result.conflicts == []
        assert dates(result.merged) == [TENDER, CLOSE]

    def test_reordering_alone_is_not_a_change(self) -> None:
        theirs = project(TENDER, ("Financial close", "2026-11-11"))

        result = merge(BASE, project(CLOSE, TENDER), theirs)

        assert result.conflicts == []
        assert result.merged == theirs

    def test_their_reordering_alone_does_not_count_as_a_change(self) -> None:
        assert merge(BASE, BASE, project(CLOSE, TENDER)).theirs_changed is False


class TestRepeatedLabels:
    DUPLICATED = project(TENDER, TENDER[:1] + ("2026-05-05",), CLOSE)

    def test_whole_list_is_one_field_when_a_label_repeats(self) -> None:
        mine = project(TENDER, ("Tender launch", "2026-05-05"), ("Financial close", "2026-10-10"))
        theirs = project(TENDER, ("Tender launch", "2026-06-06"), CLOSE)

        result = merge(self.DUPLICATED, mine, theirs)

        [conflict] = result.conflicts
        assert (conflict.field, conflict.label) == ("key_dates", None)
        assert conflict.mine == mine.key_dates
        assert conflict.theirs == theirs.key_dates
        assert result.merged.key_dates == theirs.key_dates

    def test_whole_list_takes_mine_when_only_i_changed_it(self) -> None:
        mine = project(TENDER, CLOSE)

        result = merge(self.DUPLICATED, mine, self.DUPLICATED)

        assert result.conflicts == []
        assert result.merged.key_dates == mine.key_dates

    def test_other_fields_still_merge_when_the_list_is_untouched(self) -> None:
        mine = self.DUPLICATED.model_copy(update={"name": "Mine"})
        theirs = self.DUPLICATED.model_copy(update={"country": "Peru"})

        result = merge(self.DUPLICATED, mine, theirs)

        assert result.conflicts == []
        assert (result.merged.name, result.merged.country) == ("Mine", "Peru")
        assert result.merged.key_dates == self.DUPLICATED.key_dates
