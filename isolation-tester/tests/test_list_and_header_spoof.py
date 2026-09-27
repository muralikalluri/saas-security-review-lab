"""Deliberately insecure for demonstration. Do not deploy.

list-foreign-rows and header-spoof probes (SPEC.md section 3.3) for the
plain list endpoints: GET /invoices and GET /customers (header-spoof =
A-04) and GET /invoices/search (a positive control - uses tokenTenantId,
not spoofable, no finding). The dashboard's header-spoof case (also A-04)
is handled separately in test_01_dashboard.py because it is entangled
with cache ordering (A-06) on that one endpoint.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant, all_ids_for_resource
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import run_list_probe

pytestmark = pytest.mark.order_phase(20)

_CONFIG = runtime.get_config()
_OPERATIONS = runtime.get_operations()

_RESOURCE_FOR_PATH = {
    "/invoices": "invoice",
    "/customers": "customer",
    "/invoices/search": "invoice",
}


def _own_and_foreign_ids(actor_tenant_id: str, resource: str):
    by_tenant = all_ids_for_resource(_CONFIG, resource)
    own = set(by_tenant.get(actor_tenant_id, []))
    foreign: set = set()
    for tid, ids in by_tenant.items():
        if tid != actor_tenant_id:
            foreign |= set(ids)
    return own, foreign


_LIST_CASES = []
for _op, _probe in operations_with_probe(_OPERATIONS, "list-foreign-rows"):
    _resource = _RESOURCE_FOR_PATH[_op.path]
    for _tenant in _CONFIG.tenants:
        _own, _foreign = _own_and_foreign_ids(_tenant.id, _resource)
        for _actor in actors_for_tenant(_CONFIG, _tenant):
            _LIST_CASES.append((_op.path, _actor, _foreign, _own, _probe.finding))

_LIST_IDS = [f"{p}:{a.label}" for p, a, _, _, _ in _LIST_CASES]


@pytest.mark.parametrize("path,actor,foreign_ids,own_ids,finding", _LIST_CASES, ids=_LIST_IDS)
def test_list_endpoint_never_returns_foreign_rows(client, collector, run_dir, path, actor, foreign_ids, own_ids, finding):
    run_list_probe(
        client,
        collector,
        run_dir,
        probe_type="list-foreign-rows",
        finding=finding,
        actor=actor,
        method="GET",
        path=path,
        foreign_ids=foreign_ids,
        own_ids=own_ids,
    )


_SPOOF_CASES = []
for _op, _probe in operations_with_probe(_OPERATIONS, "header-spoof"):
    if _op.path == "/dashboard/summary":
        continue  # handled in test_01_dashboard.py
    _resource = _RESOURCE_FOR_PATH[_op.path]
    for _caller_tenant in _CONFIG.tenants:
        for _spoof_tenant in _CONFIG.tenants:
            if _caller_tenant.id == _spoof_tenant.id:
                continue
            _own, _ = _own_and_foreign_ids(_caller_tenant.id, _resource)
            _spoofed_ids = set(all_ids_for_resource(_CONFIG, _resource).get(_spoof_tenant.id, []))
            for _actor in actors_for_tenant(_CONFIG, _caller_tenant):
                _SPOOF_CASES.append((_op.path, _actor, _spoof_tenant.id, _spoofed_ids, _own, _probe.finding))

_SPOOF_IDS = [f"{p}:{a.label}:spoof={s}" for p, a, s, _, _, _ in _SPOOF_CASES]


@pytest.mark.parametrize("path,actor,spoof_tenant_id,foreign_ids,own_ids,finding", _SPOOF_CASES, ids=_SPOOF_IDS)
def test_header_spoof_does_not_override_token_tenant(
    client, collector, run_dir, path, actor, spoof_tenant_id, foreign_ids, own_ids, finding
):
    run_list_probe(
        client,
        collector,
        run_dir,
        probe_type="header-spoof",
        finding=finding,
        actor=actor,
        method="GET",
        path=path,
        foreign_ids=foreign_ids,
        own_ids=own_ids,
        headers={"X-Tenant-Id": spoof_tenant_id},
    )
