"""Deliberately insecure for demonstration. Do not deploy.

A-05: GET /invoices/exports/{id} BOLA. Export ids only exist once the
harness creates them at session start (runtime_fixtures), so - unlike
invoices/customers (test_bola.py) - this can't be a module-level
parametrize table; it loops inside one test body instead, recording every
combination even if an earlier one leaks, and asserting once at the end.
"""

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import foreign_actors
from isolation_tester.oracle import Verdict
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import record_bola

pytestmark = pytest.mark.order_phase(10)

_CONFIG = runtime.get_config()
_OPERATION, _PROBE = next(
    (o, p) for o, p in operations_with_probe(runtime.get_operations(), "bola") if o.path == "/invoices/exports/{id}"
)


def test_export_bola_foreign_id_denied(client, collector, run_dir, runtime_fixtures):
    failures = []
    for tenant in _CONFIG.tenants:
        for export_id in runtime_fixtures.export_ids_for(tenant.id):
            for actor in foreign_actors(_CONFIG, tenant.id):
                result = record_bola(
                    client,
                    collector,
                    run_dir,
                    finding=_PROBE.finding,
                    actor=actor,
                    method="GET",
                    path=_OPERATION.path.format(id=export_id),
                )
                if result.verdict in (Verdict.LEAK.value, Verdict.ERROR.value):
                    failures.append(f"{result.actor} -> {result.verdict}: {result.detail}")
    assert not failures, "\n".join(failures)
