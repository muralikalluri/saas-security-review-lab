"""Deliberately insecure for demonstration. Do not deploy.

GET /dashboard/summary carries TWO distinct probe types that are causally
entangled on this specific endpoint: header-spoof (A-04, TenantContext
trusts X-Tenant-Id) and cache-order (A-06, the totals cache key is not
tenant-qualified). Both depend on cache state, so unlike every other
probe in this suite they cannot be expressed as independent parametrized
cases - this module hand-sequences both, with explicit cache resets
in between, and runs before anything else (order_phase=1) so no other
test's dashboard/list traffic can pollute the cache first.
"""

import time

import pytest

from isolation_tester import runtime
from isolation_tester.fixtures_data import actors_for_tenant
from isolation_tester.oracle import Classification, Verdict
from isolation_tester.openapi_loader import operations_with_probe
from isolation_tester.probes import record_probe

pytestmark = pytest.mark.order_phase(1)

_CONFIG = runtime.get_config()
_OPERATIONS = runtime.get_operations()
_CACHE_FINDING = next(
    p.finding for o, p in operations_with_probe(_OPERATIONS, "cache-order") if o.path == "/dashboard/summary"
)
_SPOOF_FINDING = next(
    p.finding for o, p in operations_with_probe(_OPERATIONS, "header-spoof") if o.path == "/dashboard/summary"
)


def _tenant_owner(tenant_id: str):
    tenant = _CONFIG.tenant_by_id(tenant_id)
    return next(a for a in actors_for_tenant(_CONFIG, tenant) if a.role == "owner")


def _own_invoice_total(client, actor) -> float | None:
    response = client.call("get", "/invoices", actor)
    if response.status_code != 200:
        return None
    try:
        rows = response.json()
        return round(sum(float(r["amount"]) for r in rows), 2)
    except (ValueError, KeyError, TypeError):
        return None


def _wait_out_cache():
    time.sleep(_CONFIG.cache_ttl_seconds + 1)


def _dashboard_total(response):
    """None means "could not read a total" - NEVER treat that as denied."""
    if response.status_code != 200:
        return None, None
    try:
        body = response.json()
        return float(body["totalAmount"]), body.get("source")
    except (ValueError, KeyError, TypeError):
        return None, None


def test_dashboard_cache_and_header_spoof(client, collector, run_dir):
    if len(_CONFIG.tenants) < 2:
        pytest.skip("need at least two tenants configured")

    tenant_a, tenant_b = _CONFIG.tenants[0], _CONFIG.tenants[1]
    owner_a, owner_b = _tenant_owner(tenant_a.id), _tenant_owner(tenant_b.id)

    # --- A-06 cache-order probe -------------------------------------
    _wait_out_cache()
    warm_resp = client.call("get", "/dashboard/summary", owner_a)  # warms the cache with tenant A's total
    resp_b = client.call("get", "/dashboard/summary", owner_b)
    total_b, source_b = _dashboard_total(resp_b)
    ground_truth_b = _own_invoice_total(client, owner_b)

    if warm_resp.status_code != 200 or total_b is None or ground_truth_b is None:
        classification = Classification(
            Verdict.ERROR,
            f"could not establish ground truth (warm-up status {warm_resp.status_code}, "
            f"probe status {resp_b.status_code})",
        )
    elif source_b == "cache" and total_b != ground_truth_b:
        classification = Classification(
            Verdict.LEAK,
            f"{owner_b.label} saw a cached total of {total_b} (tenant-agnostic cache key) "
            f"instead of their own ground truth {ground_truth_b} (populated by {owner_a.label}'s request)",
        )
    elif total_b == ground_truth_b:
        classification = Classification(Verdict.DENIED, f"{owner_b.label} correctly saw their own total {ground_truth_b}")
    else:
        classification = Classification(Verdict.ERROR, f"unexpected dashboard total {total_b} vs ground truth {ground_truth_b}")

    cache_result = record_probe(
        collector,
        run_dir,
        probe_id=f"cache-order:/dashboard/summary:{owner_a.label}->{owner_b.label}",
        probe_type="cache-order",
        finding=_CACHE_FINDING,
        actor=owner_b,
        method="GET",
        path="/dashboard/summary",
        classification=classification,
        request_headers={},
        request_body=None,
        response=resp_b,
    )

    # --- A-04 header-spoof probe on the same endpoint ----------------
    _wait_out_cache()  # guarantee a clean cache before the spoof attempt
    ground_truth_a = _own_invoice_total(client, owner_a)
    headers = {"X-Tenant-Id": tenant_a.id}
    resp_spoof = client.call("get", "/dashboard/summary", owner_b, headers=headers)
    total_spoof, _ = _dashboard_total(resp_spoof)

    if total_spoof is None or ground_truth_a is None:
        spoof_classification = Classification(
            Verdict.ERROR, f"could not establish ground truth (probe status {resp_spoof.status_code})"
        )
    elif abs(total_spoof - ground_truth_a) < 0.01:
        spoof_classification = Classification(
            Verdict.LEAK,
            f"{owner_b.label} spoofed X-Tenant-Id={tenant_a.id} and received tenant {tenant_a.id}'s "
            f"total ({ground_truth_a}) instead of their own",
        )
    else:
        spoof_classification = Classification(Verdict.DENIED, "spoofed header did not change whose total was computed")

    spoof_result = record_probe(
        collector,
        run_dir,
        probe_id=f"header-spoof:/dashboard/summary:{owner_b.label}:spoof={tenant_a.id}",
        probe_type="header-spoof",
        finding=_SPOOF_FINDING,
        actor=owner_b,
        method="GET",
        path="/dashboard/summary",
        classification=spoof_classification,
        request_headers=headers,
        request_body=None,
        response=resp_spoof,
    )

    failures = [r for r in (cache_result, spoof_result) if r.verdict in (Verdict.LEAK.value, Verdict.ERROR.value)]
    assert not failures, "; ".join(f"{r.probe_type}: {r.detail}" for r in failures)
