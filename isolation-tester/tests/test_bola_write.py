"""Deliberately insecure for demonstration. Do not deploy.

A-02: PUT /customers/{id} BOLA-write. Mutating, so it runs LAST
(order_phase=90) and restores the original values immediately after each
attempt that succeeds, so a re-run of this suite (or the exploit scripts)
sees the same fixture data.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import foreign_actors, owned_ids
from isolation_tester.http_client import Actor
from isolation_tester.oracle import Verdict, bola_verdict
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import assert_not_leaked, record_probe

pytestmark = pytest.mark.order_phase(90)

_CONFIG = runtime.get_config()
_OPERATION, _PROBE = next(
    (o, p) for o, p in operations_with_probe(runtime.get_operations(), "bola-write") if o.path == "/customers/{id}"
)


def _owner_actor(tenant) -> Actor:
    for role, cred in tenant.users.items():
        if role == "owner":
            return Actor(tenant=tenant, role=role, cred=cred)
    raise KeyError(f"tenant {tenant.id} has no owner user configured")


_CASES = []
for _tenant in _CONFIG.tenants:
    for _customer_id in owned_ids(_tenant, "customer"):
        for _actor in foreign_actors(_CONFIG, _tenant.id):
            _CASES.append((_tenant, _customer_id, _actor))

_IDS = [f"customer={cid}:{a.label}" for _, cid, a in _CASES]


@pytest.mark.parametrize("owning_tenant,customer_id,actor", _CASES, ids=_IDS)
def test_bola_write_foreign_customer_denied(client, collector, run_dir, owning_tenant, customer_id, actor):
    owner = _owner_actor(owning_tenant)
    path = _OPERATION.path.format(id=customer_id)

    original = client.call("get", path, owner).json()

    body = {
        "name": f"ISOLATION-TESTER PROBE (should be reverted) actor={actor.label}",
        "email": original.get("email"),
        "phone": original.get("phone"),
    }
    response = client.call("put", path, actor, json_body=body)
    classification = bola_verdict(response)
    result = record_probe(
        collector,
        run_dir,
        probe_id=f"bola-write:{path}:{actor.label}",
        probe_type="bola-write",
        finding=_PROBE.finding,
        actor=actor,
        method="PUT",
        path=path,
        classification=classification,
        request_headers={},
        request_body=body,
        response=response,
    )

    if classification.verdict == Verdict.LEAK and _OPERATION.restore:
        restore_body = {"name": original["name"], "email": original.get("email"), "phone": original.get("phone")}
        client.call("put", path, owner, json_body=restore_body)

    assert_not_leaked(result)
