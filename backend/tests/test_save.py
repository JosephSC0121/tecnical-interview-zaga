from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.harness import Upstream, form_fields

PID = "P-1001"
URL = f"/api/projects/{PID}"
Backend = Callable[[Upstream], TestClient]
FlakyUpstream = Callable[..., Upstream]

TIMEOUT, NO_TIMEOUT = 0.0, 0.5
APPLIED, LOST = 0.0, 0.9


def load(client: TestClient) -> dict[str, Any]:
    """What an editor has in the form after opening the project."""
    project = client.get(URL).json()
    del project["id"]
    return project


def save(client: TestClient, base: dict[str, Any], **changes: Any) -> httpx.Response:
    return client.put(URL, json={"base": base, "changes": changes})


def other_stage(*taken: str) -> str:
    return next(s for s in ("idea", "feasibility", "tender", "financing") if s not in taken)


class TestSingleEditor:
    def test_changed_core_fields_are_stored_and_nothing_else_moves(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        before = upstream.record(PID)
        base = load(client)
        stage = other_stage(base["stage"])

        response = save(client, base, name="Renamed", stage=stage)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "saved"
        assert body["merged_with_others"] is False
        assert (body["project"]["name"], body["project"]["stage"]) == ("Renamed", stage)
        assert upstream.record(PID) == before | {"name": "Renamed", "stage": stage}

    def test_key_dates_can_be_changed_removed_and_added(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        first, second, *rest = base["key_dates"]
        edited = [
            {"label": first["label"], "date": "2031-01-01"},
            *rest,
            {"label": "Ribbon cutting", "date": "2032-02-02"},
        ]

        response = save(client, base, key_dates=edited)

        assert response.status_code == 200
        assert upstream.record(PID)["key_dates"] == edited
        assert second not in upstream.record(PID)["key_dates"]

    def test_linked_companies_come_from_the_record_as_it_is_at_save_time(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        imported = [{"name": "Imported Capital SA", "role": "financier"}]
        upstream.write(PID, linked_companies=imported)

        response = save(client, base, name="Renamed")

        assert response.status_code == 200
        assert upstream.record(PID)["linked_companies"] == imported
        assert upstream.record(PID)["name"] == "Renamed"

    @pytest.mark.parametrize("changes", [{}, {"name": None}, "same as base"])
    def test_no_changes_writes_nothing(
        self, client: TestClient, upstream: Upstream, changes: Any
    ) -> None:
        base = load(client)

        response = client.put(
            URL, json={"base": base, "changes": base if changes == "same as base" else changes}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "unchanged"
        assert response.json()["project"] == base | {"id": PID}
        assert upstream.spy.count("PUT") == 0

    def test_unknown_project_is_404(self, client: TestClient) -> None:
        response = client.put(
            "/api/projects/P-0000", json={"base": load(client), "changes": {"name": "X"}}
        )

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "changes",
        [
            {"name": "   "},
            {"country": ""},
            {"sector": "space"},
            {"stage": "not-a-stage"},
            {"key_dates": [{"label": " ", "date": "2030-01-01"}]},
            {"key_dates": [{"label": "Launch", "date": "2030-02-30"}]},
            {
                "key_dates": [
                    {"label": "Launch", "date": "2030-01-01"},
                    {"label": " launch ", "date": "2030-06-01"},
                ]
            },
        ],
    )
    def test_invalid_edits_are_refused_before_anything_is_sent(
        self, client: TestClient, upstream: Upstream, changes: dict[str, Any]
    ) -> None:
        base = load(client)
        calls_before = len(upstream.spy.calls)

        response = save(client, base, **changes)

        assert response.status_code == 422
        assert response.json()["detail"]
        assert len(upstream.spy.calls) == calls_before

    def test_a_record_that_already_has_repeated_labels_can_have_other_fields_edited(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        repeated = [
            {"label": "Launch", "date": "2030-01-01"},
            {"label": "Launch", "date": "2030-06-01"},
        ]
        upstream.write(PID, key_dates=repeated)
        base = load(client)

        response = save(client, base, name="Renamed", key_dates=repeated)

        assert response.status_code == 200
        assert upstream.record(PID)["name"] == "Renamed"
        assert upstream.record(PID)["key_dates"] == repeated

    def test_upstream_rejection_reaches_the_editor_with_its_reason(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        reason = [{"loc": ["body", "name"], "msg": "rejected by the records system"}]
        upstream.spy.respond_call(
            len(upstream.spy.calls) + 2, httpx.Response(422, json={"detail": reason})
        )

        response = save(client, base, name="Renamed")

        assert response.status_code == 422
        assert response.json()["detail"] == reason


class TestTwoEditors:
    """The other writer saves straight to the upstream: a second instance, or the nightly import."""

    def test_different_fields_both_survive(self, client: TestClient, upstream: Upstream) -> None:
        base = load(client)
        upstream.write(PID, name="Ana's name")

        response = save(client, base, country="Peru")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert response.json()["merged_with_others"] is True
        stored = upstream.record(PID)
        assert (stored["name"], stored["country"]) == ("Ana's name", "Peru")

    def test_same_field_is_a_conflict_and_nothing_is_written(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        theirs, mine = other_stage(base["stage"]), "cancelled"
        upstream.write(PID, stage=theirs)

        response = save(client, base, stage=mine, country="Peru")

        assert response.status_code == 409
        body = response.json()
        assert body["status"] == "conflict"
        assert body["conflicts"] == [
            {"field": "stage", "label": None, "base": base["stage"], "mine": mine, "theirs": theirs}
        ]
        assert body["current"] == form_fields(upstream.record(PID))
        assert body["merged"] == body["current"] | {"country": "Peru"}
        assert upstream.spy.count("PUT") == 0
        assert upstream.record(PID)["country"] == base["country"]

    def test_resolving_a_conflict_keeps_the_choice_and_everyone_s_other_changes(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.write(PID, stage=other_stage(base["stage"]), name="Ana's name")
        conflict = save(client, base, stage="cancelled", country="Peru").json()

        resolved = conflict["merged"] | {"stage": "cancelled"}
        response = client.put(URL, json={"base": conflict["current"], "changes": resolved})

        assert response.status_code == 200
        stored = upstream.record(PID)
        assert (stored["stage"], stored["country"], stored["name"]) == (
            "cancelled",
            "Peru",
            "Ana's name",
        )

    def test_choosing_their_value_still_saves_my_other_changes(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        theirs = other_stage(base["stage"])
        upstream.write(PID, stage=theirs)
        conflict = save(client, base, stage="cancelled", country="Peru").json()

        response = client.put(
            URL, json={"base": conflict["current"], "changes": conflict["merged"]}
        )

        assert response.status_code == 200
        stored = upstream.record(PID)
        assert (stored["stage"], stored["country"]) == (theirs, "Peru")

    def test_a_further_change_before_the_resolution_is_checked_again(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.write(PID, stage=other_stage(base["stage"]))
        conflict = save(client, base, stage="cancelled").json()
        newer = other_stage(base["stage"], conflict["current"]["stage"])
        upstream.write(PID, stage=newer)

        response = client.put(
            URL,
            json={
                "base": conflict["current"],
                "changes": conflict["merged"] | {"stage": "cancelled"},
            },
        )

        assert response.status_code == 409
        assert response.json()["conflicts"][0]["theirs"] == newer
        assert upstream.record(PID)["stage"] == newer

    def test_different_key_dates_both_survive(self, client: TestClient, upstream: Upstream) -> None:
        base = load(client)
        first, second, *rest = base["key_dates"]
        upstream.write(PID, key_dates=[first | {"date": "2031-01-01"}, second, *rest])

        response = save(client, base, key_dates=[first, second | {"date": "2032-02-02"}, *rest])

        assert response.status_code == 200
        assert upstream.record(PID)["key_dates"] == [
            first | {"date": "2031-01-01"},
            second | {"date": "2032-02-02"},
            *rest,
        ]

    def test_same_key_date_conflicts_on_that_key_date_only(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        first, *rest = base["key_dates"]
        upstream.write(PID, key_dates=[first | {"date": "2031-01-01"}, *rest])

        response = save(client, base, key_dates=[first | {"date": "2032-02-02"}, *rest])

        assert response.status_code == 409
        assert response.json()["conflicts"] == [
            {
                "field": "key_dates",
                "label": first["label"],
                "base": first["date"],
                "mine": "2032-02-02",
                "theirs": "2031-01-01",
            }
        ]

    def test_removing_a_key_date_someone_else_changed_conflicts(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        first, *rest = base["key_dates"]
        upstream.write(PID, key_dates=[first | {"date": "2031-01-01"}, *rest])

        response = save(client, base, key_dates=rest)

        assert response.status_code == 409
        [conflict] = response.json()["conflicts"]
        assert (conflict["label"], conflict["mine"]) == (first["label"], None)

    def test_the_identical_change_by_both_is_saved_without_writing(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.write(PID, name="Agreed name")

        response = save(client, base, name="Agreed name")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert upstream.spy.count("PUT") == 0

    def test_a_change_between_my_write_and_the_read_back_is_reported(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        put_call = len(upstream.spy.calls) + 2
        upstream.spy.after_call(put_call, lambda: upstream.write(PID, country="Peru"))

        response = save(client, base, name="Renamed")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "changed_during_save"
        assert (body["project"]["name"], body["project"]["country"]) == ("Renamed", "Peru")

    def test_an_acknowledged_write_is_saved_even_if_the_read_back_fails(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.spy.fail_from(len(upstream.spy.calls) + 3)

        response = save(client, base, name="Renamed")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert response.json()["project"]["name"] == "Renamed"
        assert upstream.record(PID)["name"] == "Renamed"

    def test_two_backend_instances_give_the_same_guarantees(
        self, upstream: Upstream, backend: Backend
    ) -> None:
        instance_a, instance_b = backend(upstream), backend(upstream)
        base_a, base_b = load(instance_a), load(instance_b)
        mine, theirs = "cancelled", other_stage(base_a["stage"])

        assert save(instance_a, base_a, name="Ana's name", stage=theirs).status_code == 200
        merged = save(instance_b, base_b, country="Peru")
        conflicted = save(instance_b, base_b, stage=mine)

        assert merged.status_code == 200
        assert conflicted.status_code == 409
        stored = upstream.record(PID)
        assert (stored["name"], stored["country"], stored["stage"]) == (
            "Ana's name",
            "Peru",
            theirs,
        )


class TestUnreliableUpstream:
    def test_timeout_that_was_applied_is_reported_as_saved(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, APPLIED)
        client = backend(upstream)

        response = save(client, load(client), name="Renamed")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert upstream.record(PID)["name"] == "Renamed"
        assert upstream.spy.count("PUT") == 1

    def test_timeout_that_was_lost_is_retried_once(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, LOST, NO_TIMEOUT)
        client = backend(upstream)

        response = save(client, load(client), name="Renamed")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert upstream.record(PID)["name"] == "Renamed"
        assert upstream.spy.count("PUT") == 2

    def test_two_lost_timeouts_end_as_not_saved(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, LOST, TIMEOUT, LOST)
        client = backend(upstream)
        before = upstream.record(PID)

        response = save(client, load(client), name="Renamed")

        assert response.status_code == 503
        assert response.json() == {"status": "not_saved"}
        assert upstream.record(PID) == before
        assert upstream.spy.count("PUT") == 2

    def test_retry_that_times_out_but_lands_is_saved(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, LOST, TIMEOUT, APPLIED)
        client = backend(upstream)

        response = save(client, load(client), name="Renamed")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert upstream.record(PID)["name"] == "Renamed"

    def test_retry_goes_through_the_merge_and_can_find_a_conflict(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, LOST)
        client = backend(upstream)
        base = load(client)
        theirs = other_stage(base["stage"])
        put_call = len(upstream.spy.calls) + 2
        upstream.spy.after_call(put_call, lambda: upstream.write(PID, stage=theirs))

        response = save(client, base, stage="cancelled")

        assert response.status_code == 409
        assert upstream.record(PID)["stage"] == theirs
        assert upstream.spy.count("PUT") == 1

    def test_retry_keeps_a_change_that_arrived_in_between(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, LOST)
        client = backend(upstream)
        base = load(client)
        put_call = len(upstream.spy.calls) + 2
        upstream.spy.after_call(put_call, lambda: upstream.write(PID, country="Peru"))

        response = save(client, base, name="Renamed")

        assert response.status_code == 200
        assert response.json()["merged_with_others"] is True
        stored = upstream.record(PID)
        assert (stored["name"], stored["country"]) == ("Renamed", "Peru")

    def test_timeout_that_cannot_be_checked_is_unconfirmed_then_resolved_by_resending(
        self, flaky_upstream: FlakyUpstream, backend: Backend
    ) -> None:
        upstream = flaky_upstream(TIMEOUT, APPLIED)
        client = backend(upstream)
        base = load(client)
        upstream.spy.fail_from(len(upstream.spy.calls) + 3)

        unconfirmed = save(client, base, name="Renamed")

        assert unconfirmed.status_code == 504
        assert unconfirmed.json() == {"status": "unconfirmed"}

        upstream.spy.fail_from(None)
        checked_again = save(client, base, name="Renamed")

        assert checked_again.status_code == 200
        assert checked_again.json()["status"] == "saved"
        assert upstream.spy.count("PUT") == 1

    def test_transport_error_on_the_write_is_reconciled_like_a_timeout(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.spy.fail_call(len(upstream.spy.calls) + 2)

        response = save(client, base, name="Renamed")

        assert response.status_code == 200
        assert response.json()["status"] == "saved"
        assert upstream.record(PID)["name"] == "Renamed"
        assert upstream.spy.count("PUT") == 2

    def test_failed_first_read_is_502_and_nothing_is_written(
        self, client: TestClient, upstream: Upstream
    ) -> None:
        base = load(client)
        upstream.spy.fail_from(len(upstream.spy.calls) + 1)

        response = save(client, base, name="Renamed")

        assert response.status_code == 502
        assert upstream.spy.count("PUT") == 0
