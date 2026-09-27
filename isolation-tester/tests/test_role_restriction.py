"""Deliberately insecure for demonstration. Do not deploy.

A-07: POST /users/invite BFLA. Probes every role configured as "below"
the operation's declared min_role (SPEC.md section 3.2: "as lower roles
within Tenant 1" - generalised here to every tenant that has a role
hierarchy, not just Tenant 1).
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import run_role_probe

pytestmark = pytest.mark.order_phase(30)

_CONFIG = runtime.get_config()
_OPERATIONS = runtime.get_operations()

_ROLE_RANK = {"owner": 3, "admin": 2, "accountant": 1, "viewer": 0}

_CASES = []
for _op, _probe in operations_with_probe(_OPERATIONS, "role-restricted"):
    min_rank = _ROLE_RANK.get(_op.min_role, 0)
    for _tenant in _CONFIG.tenants:
        for _actor in actors_for_tenant(_CONFIG, _tenant):
            if _ROLE_RANK.get(_actor.role, 0) < min_rank:
                _CASES.append((_op.path, _actor, _probe.finding))

_IDS = [f"{p}:{a.label}" for p, a, _ in _CASES]


@pytest.mark.parametrize("path,actor,finding", _CASES, ids=_IDS)
def test_role_below_minimum_is_denied(client, collector, run_dir, path, actor, finding):
    body = {"email": f"probe+{actor.role}@{actor.tenant.id}.example", "role": "admin"}
    run_role_probe(client, collector, run_dir, finding=finding, actor=actor, method="POST", path=path, body=body)
