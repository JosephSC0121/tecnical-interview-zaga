"""Runs the real upstream app in-process, deterministically, behind a transport that spies."""

import random
from collections.abc import Callable
from typing import Any

import httpx
from fastapi.testclient import TestClient
from records_api.main import API_KEY, create_app

FORM_FIELDS = ("name", "sector", "country", "stage", "key_dates")
EDITABLE_FIELDS = (*FORM_FIELDS, "linked_companies")
NO_TIMEOUT = 0.99


class FixedRandom(random.Random):
    """random() returns the given values in turn, then a value that triggers nothing."""

    def __init__(self, *values: float) -> None:
        super().__init__()
        self.values = list(values)

    def random(self) -> float:
        return self.values.pop(0) if self.values else NO_TIMEOUT


class UpstreamSpy(httpx.AsyncBaseTransport):
    """Forwards our backend's calls to the upstream app, counting them from 1."""

    def __init__(self, upstream_app: Any) -> None:
        self._inner = httpx.ASGITransport(app=upstream_app)
        self.calls: list[tuple[str, str]] = []
        self._after: dict[int, Callable[[], None]] = {}
        self._canned: dict[int, httpx.Response] = {}
        self._failing: set[int] = set()
        self._failing_from: int | None = None

    def after_call(self, n: int, callback: Callable[[], None]) -> None:
        self._after[n] = callback

    def respond_call(self, n: int, response: httpx.Response) -> None:
        self._canned[n] = response

    def fail_call(self, n: int) -> None:
        self._failing.add(n)

    def fail_from(self, n: int | None) -> None:
        self._failing_from = n

    def count(self, method: str) -> int:
        return sum(1 for called, _ in self.calls if called == method)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        n = len(self.calls)
        if n in self._failing or (self._failing_from is not None and n >= self._failing_from):
            raise httpx.ConnectError("upstream unreachable", request=request)
        response = self._canned.get(n) or await self._inner.handle_async_request(request)
        if callback := self._after.pop(n, None):
            callback()
        return response


class Upstream:
    """The upstream app, the spy our backend goes through, and a direct line for other writers."""

    def __init__(self, *random_values: float) -> None:
        app = create_app(rng=FixedRandom(*random_values))
        self.spy = UpstreamSpy(app)
        self._direct = TestClient(app, headers={"X-Api-Key": API_KEY})

    def http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self.spy, base_url="http://upstream", headers={"X-Api-Key": API_KEY}
        )

    def record(self, project_id: str) -> dict[str, Any]:
        return self._direct.get(f"/projects/{project_id}").json()

    def write(self, project_id: str, **changes: Any) -> None:
        """Another writer (a second editor's instance, or the nightly import) saves directly."""
        record = self.record(project_id)
        body = {field: record[field] for field in EDITABLE_FIELDS} | changes
        response = self._direct.put(f"/projects/{project_id}", json=body)
        assert response.status_code == 200, response.text


def form_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record[field] for field in FORM_FIELDS}
