"""Deliberately insecure for demonstration. Do not deploy.

id-enumeration probes (SPEC.md section 3.3). Walks a small id range beyond
the known fixture ids - wider than a single-id BOLA check - for invoices
(A-01) and exports (A-05), using one prober per resource type so the
count of probes stays proportional to the id range, not to
actors x ids x resource types.

Ownership ground truth matters here more than anywhere else in this
suite: on a long-lived dev stack, the seed/fixture ids are NOT the only
ids a tenant legitimately owns (earlier manual runs, exploit scripts, or
earlier isolation-tester runs all create more). For invoices we can get
the true live ownership set with a single GET as the prober; for exports
there is no such list endpoint in the app at all, so instead of walking
a wide range and guessing, we only probe ids we can classify with
certainty: this run's own/foreign export ids, plus a small buffer of ids
past the global max that are certainly nonexistent. Anything else is
genuinely ambiguous (could be the prober's own tenant's export from an
earlier run) and is deliberately NOT probed, rather than risking a false
LEAK - see B3 in the M2 milestone review.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import run_id_enumeration_probe

pytestmark = pytest.mark.order_phase(15)

_CONFIG = runtime.get_config()
_OPERATIONS = runtime.get_operations()


def _prober_for(tenant_id: str):
    tenant = _CONFIG.tenant_by_id(tenant_id)
    return next(iter(actors_for_tenant(_CONFIG, tenant)))


def _probe_one(client, collector, run_dir, finding, prober, path_template, resource_id, own_ids):
    run_id_enumeration_probe(
        client,
        collector,
        run_dir,
        finding=finding,
        actor=prober,
        method="GET",
        path_template=path_template,
        resource_id=resource_id,
        own_ids=own_ids,
    )


def test_invoice_id_enumeration(client, collector, run_dir, runtime_fixtures):
    op, probe = next((o, p) for o, p in operations_with_probe(_OPERATIONS, "id-enum") if o.path == "/invoices/{id}")

    prober_tenant = _CONFIG.tenants[-1]  # the tenant with fewer roles is enough to prove the point
    prober = _prober_for(prober_tenant.id)

    # Live ground truth, not the static config/runtime_fixtures ids: this is
    # the actual fix for B3 - whatever the prober's tenant genuinely owns
    # right now, including ids created by unrelated earlier runs.
    own_ids = {row["id"] for row in client.call("get", "/invoices", prober).json()}

    max_id = max(own_ids | set(runtime_fixtures.extra_invoice_ids.get(prober_tenant.id, [])), default=0)
    for other_tenant in _CONFIG.tenants:
        if other_tenant.id != prober_tenant.id:
            max_id = max(max_id, max(runtime_fixtures.invoice_ids_for(_CONFIG, other_tenant.id), default=0))
    id_range = range(1, max_id + _CONFIG.enumeration_extra_ids + 1)

    failures = []
    for resource_id in id_range:
        try:
            _probe_one(client, collector, run_dir, probe.finding, prober, op.path, resource_id, own_ids)
        except AssertionError as exc:
            failures.append(str(exc))
    assert not failures, "\n".join(failures)


def test_export_id_enumeration(client, collector, run_dir, runtime_fixtures):
    op_probes = [(o, p) for o, p in operations_with_probe(_OPERATIONS, "id-enum") if o.path == "/invoices/exports/{id}"]
    if not op_probes:
        pytest.skip("no id-enum probe declared for the export endpoint")
    op, probe = op_probes[0]

    prober_tenant = _CONFIG.tenants[-1]
    prober = _prober_for(prober_tenant.id)
    own_ids = set(runtime_fixtures.export_ids_for(prober_tenant.id))

    foreign_ids: set[int] = set()
    for tenant in _CONFIG.tenants:
        if tenant.id != prober_tenant.id:
            foreign_ids |= set(runtime_fixtures.export_ids_for(tenant.id))

    all_known_ids = own_ids | foreign_ids
    max_known = max(all_known_ids, default=0)
    nonexistent_buffer = range(max_known + 1, max_known + _CONFIG.enumeration_extra_ids + 1)

    # Only ids we can classify with certainty (see module docstring) - NOT
    # a blind range walk, which would sweep up ambiguous historical ids.
    ids_to_probe = sorted(all_known_ids) + list(nonexistent_buffer)

    failures = []
    for resource_id in ids_to_probe:
        try:
            _probe_one(client, collector, run_dir, probe.finding, prober, op.path, resource_id, own_ids)
        except AssertionError as exc:
            failures.append(str(exc))
    assert not failures, "\n".join(failures)
