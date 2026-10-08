"""Client for the upstream records API. The only module that talks to it."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.models import UpstreamRecord

Record = dict[str, Any]


class ProjectNotFound(Exception):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"Project {project_id} not found")


class UpstreamError(Exception):
    """The upstream is unreachable, answered with an error, or returned an invalid record."""


class UpstreamRejected(Exception):
    """The upstream refused a write as invalid (422)."""

    def __init__(self, detail: Any) -> None:
        super().__init__("The records system rejected the save as invalid")
        self.detail = detail


@dataclass(frozen=True)
class Written:
    record: Record


@dataclass(frozen=True)
class Ambiguous:
    """The write may or may not have been applied: a 504, a transport error or a timeout."""


PutOutcome = Written | Ambiguous


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    # The slow path of the upstream takes about 2 s; 5 s waits for it instead of failing.
    return httpx.AsyncClient(
        base_url=settings.upstream_base_url,
        headers={"X-Api-Key": settings.upstream_api_key},
        timeout=httpx.Timeout(5.0, connect=2.0),
    )


class UpstreamClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def list_projects(self) -> list[Record]:
        response = await self._get("/projects")
        records = response.json()
        if not isinstance(records, list):
            raise UpstreamError("The records system returned an invalid list")
        return [_validated(record) for record in records]

    async def get_project(self, project_id: str) -> Record:
        response = await self._get(_project_path(project_id))
        if response.status_code == httpx.codes.NOT_FOUND:
            raise ProjectNotFound(project_id)
        return _validated(response.json())

    async def put_project(self, project_id: str, body: Record) -> PutOutcome:
        try:
            response = await self._http.put(_project_path(project_id), json=body)
        except httpx.HTTPError:
            return Ambiguous()
        if response.status_code == httpx.codes.GATEWAY_TIMEOUT:
            return Ambiguous()
        if response.status_code == httpx.codes.NOT_FOUND:
            raise ProjectNotFound(project_id)
        if response.status_code == httpx.codes.UNPROCESSABLE_ENTITY:
            raise UpstreamRejected(response.json().get("detail"))
        if response.status_code != httpx.codes.OK:
            raise UpstreamError(f"The records system answered {response.status_code}")
        return Written(_validated(response.json()))

    async def _get(self, path: str) -> httpx.Response:
        try:
            response = await self._http.get(path)
        except httpx.HTTPError as error:
            raise UpstreamError("The records system is unreachable") from error
        if response.status_code not in (httpx.codes.OK, httpx.codes.NOT_FOUND):
            raise UpstreamError(f"The records system answered {response.status_code}")
        return response


def _project_path(project_id: str) -> str:
    return f"/projects/{quote(project_id, safe='')}"


def _validated(record: Any) -> Record:
    try:
        UpstreamRecord.model_validate(record)
    except ValidationError as error:
        raise UpstreamError("The records system returned an invalid record") from error
    return record
