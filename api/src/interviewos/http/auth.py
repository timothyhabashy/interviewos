from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from jose import JWTError, jwt

from interviewos.http.settings import (
    auth_bypass,
    clerk_issuer,
    clerk_jwks_url,
    guest_cookie_name,
    guest_secret,
)

GUEST_COOKIE = guest_cookie_name()


@dataclass
class Principal:
    user_id: str | None = None
    guest_id: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return bool(self.user_id)


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(guest_secret(), salt="guest")


def ensure_guest_id(request: Request, response: Response) -> str:
    header = request.headers.get("x-guest-id", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{32}", header):
        return header
    raw = request.cookies.get(GUEST_COOKIE)
    if raw:
        try:
            return str(_serializer().loads(raw))
        except BadSignature:
            pass
    guest_id = uuid.uuid4().hex
    response.set_cookie(
        GUEST_COOKIE,
        _serializer().dumps(guest_id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return guest_id


def decode_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    if auth_bypass():
        return token.strip()
    jwks_url = clerk_jwks_url()
    issuer = clerk_issuer()
    if not jwks_url:
        raise HTTPException(status_code=401, detail="Auth is not configured")
    try:
        header = jwt.get_unverified_header(token)
        from urllib.request import urlopen
        import json

        with urlopen(jwks_url, timeout=5) as resp:  # noqa: S310 - configured JWKS URL
            jwks = json.loads(resp.read().decode("utf-8"))
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown signing key")
        claims = jwt.decode(
            token,
            key,
            algorithms=[header.get("alg", "RS256")],
            issuer=issuer,
            options={"verify_aud": False},
        )
        subject = claims.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Token missing sub")
        return str(subject)
    except (JWTError, HTTPException):
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def get_principal(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
) -> Principal:
    user_id = decode_bearer(authorization)
    guest_id = ensure_guest_id(request, response)
    if user_id:
        return Principal(user_id=user_id, guest_id=guest_id)
    return Principal(guest_id=guest_id)


def assert_can_access(session_owner_id: str | None, session_guest_id: str | None, principal: Principal) -> None:
    if session_owner_id:
        if principal.user_id == session_owner_id:
            return
        raise HTTPException(status_code=403, detail="Not allowed to access this session")
    if session_guest_id and principal.guest_id == session_guest_id:
        return
    raise HTTPException(status_code=403, detail="Not allowed to access this session")
