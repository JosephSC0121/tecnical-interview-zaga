import os
from dataclasses import dataclass

DEFAULT_UPSTREAM_BASE_URL = "http://127.0.0.1:8081"


@dataclass(frozen=True)
class Settings:
    upstream_base_url: str
    upstream_api_key: str


def load_settings() -> Settings:
    api_key = os.environ.get("UPSTREAM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "UPSTREAM_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and start the server with `uv run --env-file .env ...`."
        )
    return Settings(
        upstream_base_url=os.environ.get("UPSTREAM_BASE_URL", DEFAULT_UPSTREAM_BASE_URL),
        upstream_api_key=api_key,
    )
