"""Deliberately insecure for demonstration. Do not deploy.

Helpers for reading/extending the per-tenant fixture id sets declared in
the run config, plus the resources this harness creates itself at session
start (SPEC.md section 3.1: "Creates resources as Tenant 1...").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from isolation_tester.config import RunConfig, Tenant
from isolation_tester.http_client import Actor


def actors_for_tenant(config: RunConfig, tenant: Tenant) -> list[Actor]:
    return [Actor(tenant=tenant, role=role, cred=cred) for role, cred in tenant.users.items()]


def foreign_actors(config: RunConfig, owning_tenant_id: str) -> list[Actor]:
    """Every actor in every tenant OTHER than the one that owns a resource."""
    actors: list[Actor] = []
    for tenant in config.tenants:
        if tenant.id == owning_tenant_id:
            continue
        actors.extend(actors_for_tenant(config, tenant))
    return actors


def owned_ids(tenant: Tenant, resource: str) -> list[int]:
    key = f"{resource}_ids"
    return list(tenant.fixtures.get(key, []))


def all_ids_for_resource(config: RunConfig, resource: str) -> dict[str, list[int]]:
    """tenant_id -> known ids for a resource type, across ALL tenants."""
    return {tenant.id: owned_ids(tenant, resource) for tenant in config.tenants}


@dataclass
class RuntimeFixtures:
    """Ids created by the harness itself at session start, extending the
    static config fixtures for resources that have no fixed seed data
    (exports) or need a wider id range for enumeration (invoices).
    """

    extra_invoice_ids: dict[str, list[int]] = field(default_factory=dict)
    export_ids: dict[str, list[int]] = field(default_factory=dict)

    def invoice_ids_for(self, config: RunConfig, tenant_id: str) -> list[int]:
        tenant = config.tenant_by_id(tenant_id)
        return owned_ids(tenant, "invoice") + self.extra_invoice_ids.get(tenant_id, [])

    def export_ids_for(self, tenant_id: str) -> list[int]:
        return self.export_ids.get(tenant_id, [])

    def max_id_seen(self, config: RunConfig) -> int:
        candidates = [0]
        for tenant in config.tenants:
            candidates.extend(owned_ids(tenant, "invoice"))
            candidates.extend(owned_ids(tenant, "customer"))
            candidates.extend(self.extra_invoice_ids.get(tenant.id, []))
            candidates.extend(self.export_ids.get(tenant.id, []))
        return max(candidates)
