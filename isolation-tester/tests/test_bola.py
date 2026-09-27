"""Deliberately insecure for demonstration. Do not deploy.

BOLA probes (SPEC.md section 3.2: "replay every endpoint/method as
Tenant 2 ... using Tenant 1's resource ids") for single-resource GET
endpoints whose id is fixed by config: GET /invoices/{id} (A-01) and
GET /customers/{id} (a positive control - correctly tenant-scoped, no
finding). The export endpoint's ids (A-05) are only known at runtime
(see test_export_bola.py).
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import owned_ids
from isolation_tester.fixtures_data import foreign_actors
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import run_bola_probe

pytestmark = pytest.mark.order_phase(10)

_CONFIG = runtime.get_config()
_OPERATIONS = runtime.get_operations()

_RESOURCE_FOR_PATH = {
    "/invoices/{id}": "invoice",
    "/customers/{id}": "customer",
}

_CASES = []
for _op, _probe in operations_with_probe(_OPERATIONS, "bola"):
    _resource = _RESOURCE_FOR_PATH.get(_op.path)
    if _resource is None:
        continue  # export handled separately, needs runtime-created ids
    for _tenant in _CONFIG.tenants:
        for _resource_id in owned_ids(_tenant, _resource):
            for _actor in foreign_actors(_CONFIG, _tenant.id):
                _CASES.append((_op.method, _op.path, _resource_id, _actor, _probe.finding))

_IDS = [f"{m}:{p}:id={rid}:{a.label}" for m, p, rid, a, _ in _CASES]


@pytest.mark.parametrize("method,path_template,resource_id,actor,finding", _CASES, ids=_IDS)
def test_bola_foreign_id_denied(client, collector, run_dir, method, path_template, resource_id, actor, finding):
    run_bola_probe(
        client,
        collector,
        run_dir,
        finding=finding,
        actor=actor,
        method=method,
        path_template=path_template,
        resource_id=resource_id,
    )
