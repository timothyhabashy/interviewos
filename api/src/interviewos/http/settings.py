from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv()


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+pysqlite:///:memory:")


def guest_secret() -> str:
    return os.environ.get("GUEST_COOKIE_SECRET", "interviewos-dev-guest-secret")


def guest_cookie_name() -> str:
    return "interviewos_guest"


def clerk_jwks_url() -> str | None:
    return os.environ.get("CLERK_JWKS_URL") or None


def clerk_issuer() -> str | None:
    return os.environ.get("CLERK_ISSUER") or None


def auth_bypass() -> bool:
    return os.environ.get("INTERVIEWOS_AUTH_BYPASS", "").strip() in {"1", "true", "yes"}


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


def live_mode() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
