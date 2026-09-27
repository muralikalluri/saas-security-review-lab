"""Deliberately insecure for demonstration. Do not deploy.

Positive controls: every actor must be able to read their OWN resources.
Without this, a down API or an over-aggressive "fix" that blocks everyone
(not just foreign tenants) would show a fully green matrix - which is
exactly the failure mode a security regression tool must not have.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant
from isolation_tester.probes import run_positive_control

pytestmark = pytest.mark.order_phase(0)

_CONFIG = runtime.get_config()

_CASES = []
for _tenant in _CONFIG.tenants:
    for _actor in actors_for_tenant(_CONFIG, _tenant):
        if _tenant.fixtures.get("invoice_ids"):
            _CASES.append(("GET", f"/invoices/{_tenant.fixtures['invoice_ids'][0]}", _actor))
        if _tenant.fixtures.get("customer_ids"):
            _CASES.append(("GET", f"/customers/{_tenant.fixtures['customer_ids'][0]}", _actor))
        _CASES.append(("GET", "/invoices", _actor))
        _CASES.append(("GET", "/customers", _actor))


@pytest.mark.parametrize("method,path,actor", _CASES, ids=[f"{m}:{p}:{a.label}" for m, p, a in _CASES])
def test_owner_can_access_own_resource(client, collector, run_dir, method, path, actor):
    run_positive_control(client, collector, run_dir, finding_label=f"{method}:{path}", actor=actor, method=method, path=path)
