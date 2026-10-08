from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import load_settings
from app.models import ProjectDetail, ProjectSummary, SaveRequest
from app.save import InvalidEdit, save_project
from app.upstream import (
    ProjectNotFound,
    UpstreamClient,
    UpstreamError,
    UpstreamRejected,
    build_http_client,
)


def get_upstream(request: Request) -> UpstreamClient:
    return request.app.state.upstream


Upstream = Annotated[UpstreamClient, Depends(get_upstream)]

STATUS_CODES = {
    "saved": 200,
    "unchanged": 200,
    "changed_during_save": 200,
    "conflict": 409,
    "not_saved": 503,
    "unconfirmed": 504,
}


def create_app(http_client: httpx.AsyncClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = http_client or build_http_client(load_settings())
        # A connection pool, not state about records: nothing here outlives a request's decision.
        app.state.upstream = UpstreamClient(client)
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(title="Project editor backend", lifespan=lifespan)

    @app.exception_handler(ProjectNotFound)
    async def not_found(_: Request, error: ProjectNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(UpstreamError)
    async def upstream_failed(_: Request, error: UpstreamError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(UpstreamRejected)
    async def upstream_rejected(_: Request, error: UpstreamRejected) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": error.detail})

    @app.exception_handler(InvalidEdit)
    async def invalid_edit(_: Request, error: InvalidEdit) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": error.errors})

    @app.get("/api/projects")
    async def list_projects(upstream: Upstream) -> list[ProjectSummary]:
        return [ProjectSummary.model_validate(record) for record in await upstream.list_projects()]

    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str, upstream: Upstream) -> ProjectDetail:
        return ProjectDetail.model_validate(await upstream.get_project(project_id))

    @app.put("/api/projects/{project_id}", response_model=None)
    async def save(project_id: str, request: SaveRequest, upstream: Upstream) -> JSONResponse:
        result = await save_project(upstream, project_id, request)
        return JSONResponse(
            status_code=STATUS_CODES[result.status], content=result.model_dump(mode="json")
        )

    return app
