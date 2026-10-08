from collections.abc import Callable, Iterator
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.harness import Upstream


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch) -> Upstream:
    monkeypatch.setenv("UPSTREAM_SLOW_RATE", "0")
    monkeypatch.setenv("UPSTREAM_TIMEOUT_RATE", "0")
    return Upstream()


@pytest.fixture
def flaky_upstream(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Upstream]:
    """Builds an upstream whose PUTs draw the given values: timeout if < 0.1, then applied if < 0.5."""

    def build(*random_values: float) -> Upstream:
        monkeypatch.setenv("UPSTREAM_SLOW_RATE", "0")
        monkeypatch.setenv("UPSTREAM_TIMEOUT_RATE", "0.1")
        return Upstream(*random_values)

    return build


@pytest.fixture
def backend() -> Iterator[Callable[[Upstream], TestClient]]:
    """Starts an instance of our backend against an upstream. Call it twice for two instances."""
    with ExitStack() as stack:

        def start(upstream: Upstream) -> TestClient:
            app = create_app(http_client=upstream.http_client())
            return stack.enter_context(TestClient(app))

        yield start


@pytest.fixture
def client(upstream: Upstream, backend: Callable[[Upstream], TestClient]) -> TestClient:
    return backend(upstream)
