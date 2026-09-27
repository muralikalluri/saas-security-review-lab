"""Deliberately insecure for demonstration. Do not deploy.

Loads the tenants/roles/fixtures config (SPEC.md section 3.1: "a config
with two tenants x each role's credentials").
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::([^}]*))?\}")


def _interpolate_env(value: str) -> str:
    def replace(match: re.Match) -> str:
        var_name, default = match.group(1), match.group(2)
        return os.environ.get(var_name, default if default is not None else "")

    return _ENV_PATTERN.sub(replace, value)


@dataclass
class UserCred:
    username: str
    password: str


@dataclass
class Tenant:
    id: str
    name: str
    users: dict[str, UserCred]
    fixtures: dict[str, list]


@dataclass
class ExcludedFinding:
    id: str
    reason: str


@dataclass
class RunConfig:
    base_url: str
    cache_ttl_seconds: int
    tenants: list[Tenant]
    enumeration_extra_ids: int
    excluded_findings: list[ExcludedFinding] = field(default_factory=list)

    def all_actors(self) -> list[tuple[Tenant, str, UserCred]]:
        return [(tenant, role, cred) for tenant in self.tenants for role, cred in tenant.users.items()]

    def tenant_by_id(self, tenant_id: str) -> Tenant:
        for tenant in self.tenants:
            if tenant.id == tenant_id:
                return tenant
        raise KeyError(f"no tenant configured with id {tenant_id!r}")


def load_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text())

    tenants = []
    for tenant_raw in raw["tenants"]:
        users = {
            role: UserCred(username=u["username"], password=u["password"])
            for role, u in tenant_raw["users"].items()
        }
        tenants.append(
            Tenant(
                id=tenant_raw["id"],
                name=tenant_raw["name"],
                users=users,
                fixtures=tenant_raw.get("fixtures", {}),
            )
        )

    excluded = [ExcludedFinding(id=e["id"], reason=e["reason"]) for e in raw.get("excluded_findings", [])]

    return RunConfig(
        base_url=_interpolate_env(raw["base_url"]).rstrip("/"),
        cache_ttl_seconds=int(raw.get("cache_ttl_seconds", 30)),
        tenants=tenants,
        enumeration_extra_ids=int(raw.get("enumeration", {}).get("extra_ids_beyond_max", 5)),
        excluded_findings=excluded,
    )
