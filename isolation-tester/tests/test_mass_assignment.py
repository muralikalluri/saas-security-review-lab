"""Deliberately insecure for demonstration. Do not deploy.

A-03: POST /invoices mass-assignment of tenantId. Mutating (creates a real
row), so it runs late (order_phase=85) - specifically before the BOLA-write
probes (90) since it doesn't need any restore step, just ordering after
the read-only probes and the dashboard test that depends on stable totals.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import run_mass_assignment_probe

pytestmark = pytest.mark.order_phase(85)

_CONFIG = runtime.get_config()
_OPERATION, _PROBE = next(
    (o, p) for o, p in operations_with_probe(runtime.get_operations(), "mass-assignment") if o.path == "/invoices"
)

_CASES = []
for _caller_tenant in _CONFIG.tenants:
    for _target_tenant in _CONFIG.tenants:
        if _caller_tenant.id == _target_tenant.id:
            continue
        for _actor in actors_for_tenant(_CONFIG, _caller_tenant):
            _CASES.append((_actor, _target_tenant))

_IDS = [f"{a.label}->{t.id}" for a, t in _CASES]


@pytest.mark.parametrize("actor,target_tenant", _CASES, ids=_IDS)
def test_mass_assignment_tenant_id_ignored(client, collector, run_dir, actor, target_tenant):
    body = {
        "tenantId": target_tenant.id,
        "customerId": target_tenant.fixtures["customer_ids"][0],
        "amount": "1.00",
        "internalCost": "0.50",
        "status": "draft",
    }
    run_mass_assignment_probe(
        client,
        collector,
        run_dir,
        finding=_PROBE.finding,
        actor=actor,
        method="POST",
        path=_OPERATION.path,
        body=body,
        injected_tenant_id=target_tenant.id,
    )
