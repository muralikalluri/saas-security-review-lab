"""Deliberately insecure for demonstration. Do not deploy.

Thin authenticated HTTP client + evidence capture for the isolation tester.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from isolation_tester.config import RunConfig, Tenant, UserCred


@dataclass(frozen=True)
class Actor:
    tenant: Tenant
    role: str
    cred: UserCred

    @property
    def label(self) -> str:
        return f"{self.cred.username}@{self.tenant.id}"


class AuthError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, config: RunConfig):
        self.config = config
        self._client = httpx.Client(base_url=config.base_url, timeout=10.0)
        self._token_cache: dict[str, str] = {}

    def close(self) -> None:
        self._client.close()

    def token_for(self, actor: Actor) -> str:
        cache_key = actor.label
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]
        response = self._client.post(
            "/auth/login",
            json={"username": actor.cred.username, "password": actor.cred.password},
        )
        if response.status_code != 200:
            raise AuthError(
                f"login failed for {actor.label}: HTTP {response.status_code} {response.text[:200]}"
            )
        token = response.json()["access_token"]
        self._token_cache[cache_key] = token
        return token

    def call(
        self,
        method: str,
        path: str,
        actor: Actor,
        *,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        token = self.token_for(actor)
        request_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            request_headers.update(headers)
        return self._client.request(
            method, path, json=json_body, headers=request_headers, params=params
        )

    def status_check(self) -> httpx.Response:
        return self._client.get("/api/status")


def save_evidence(
    run_dir: Path,
    probe_id: str,
    *,
    method: str,
    path: str,
    actor_label: str,
    request_headers: dict[str, str],
    request_body: Any,
    response: httpx.Response,
) -> str:
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_id = probe_id.replace("/", "_").replace(" ", "_").replace(":", "_")
    evidence_path = raw_dir / f"{safe_id}.json"
    redacted_headers = {
        k: ("Bearer ***redacted***" if k.lower() == "authorization" else v)
        for k, v in request_headers.items()
    }
    try:
        response_body: Any = response.json()
    except ValueError:
        response_body = response.text[:2000]
    payload = {
        "probe_id": probe_id,
        "actor": actor_label,
        "request": {
            "method": method,
            "path": path,
            "headers": redacted_headers,
            "body": request_body,
        },
        "response": {
            "status": response.status_code,
            "body": response_body,
        },
    }
    evidence_path.write_text(json.dumps(payload, indent=2, default=str))
    return str(evidence_path.relative_to(run_dir))
