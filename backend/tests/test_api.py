from typing import get_args

import httpx
from fastapi.testclient import TestClient
from records_api.main import API_KEY
from records_api.seed import SECTORS, STAGES

from app.models import Sector, Stage
from tests.harness import Upstream


def test_list_returns_every_project_with_only_the_list_columns(client: TestClient) -> None:
    response = client.get("/api/projects")

    assert response.status_code == 200
    projects = response.json()
    assert len(projects) == 30
    assert all(set(p) == {"id", "name", "sector", "country", "stage"} for p in projects)


def test_detail_returns_only_what_the_form_needs(client: TestClient, upstream: Upstream) -> None:
    response = client.get("/api/projects/P-1001")

    assert response.status_code == 200
    project = response.json()
    assert set(project) == {"id", "name", "sector", "country", "stage", "key_dates"}
    stored = upstream.record("P-1001")
    assert project == {field: stored[field] for field in project}


def test_unknown_project_is_404(client: TestClient) -> None:
    response = client.get("/api/projects/P-0000")

    assert response.status_code == 404
    assert "P-0000" in response.json()["detail"]


def test_unreachable_upstream_is_502(client: TestClient, upstream: Upstream) -> None:
    upstream.spy.fail_from(1)

    assert client.get("/api/projects").status_code == 502
    assert client.get("/api/projects/P-1001").status_code == 502


def test_invalid_upstream_record_is_502_not_500(client: TestClient, upstream: Upstream) -> None:
    broken = upstream.record("P-1001") | {"sector": "space"}
    upstream.spy.respond_call(1, httpx.Response(200, json=[broken]))
    upstream.spy.respond_call(2, httpx.Response(200, json=broken))

    assert client.get("/api/projects").status_code == 502
    assert client.get("/api/projects/P-1001").status_code == 502


def test_upstream_api_key_never_reaches_the_browser(client: TestClient, upstream: Upstream) -> None:
    responses = [
        client.get("/api/projects"),
        client.get("/api/projects/P-1001"),
        client.get("/api/projects/P-0000"),
    ]
    upstream.spy.fail_from(len(upstream.spy.calls) + 1)
    responses.append(client.get("/api/projects"))

    for response in responses:
        assert API_KEY not in response.text
        assert API_KEY not in str(response.headers)


def test_allowed_values_match_the_upstream() -> None:
    assert set(get_args(Sector)) == set(SECTORS)
    assert list(get_args(Stage)) == STAGES
