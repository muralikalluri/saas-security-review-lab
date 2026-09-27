"""Deliberately insecure for demonstration. Do not deploy."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from isolation_tester import runtime
from isolation_tester.fixtures_data import RuntimeFixtures, actors_for_tenant
from isolation_tester.http_client import Actor, ApiClient, AuthError
from isolation_tester.matrix import MatrixCollector


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "order_phase(n): controls probe execution order (lower runs first)")


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: list[pytest.Item]) -> None:
    def phase_of(item: pytest.Item) -> int:
        marker = item.get_closest_marker("order_phase")
        return marker.args[0] if marker else 50

    items.sort(key=phase_of)


def pytest_exception_interact(node, call, report) -> None:
    """Catches any exception NOT raised by our own assert_not_leaked/assert
    (which always means "a LEAK/ERROR row was already recorded") - e.g. an
    httpx timeout, a KeyError from an unexpected response shape, a fixture
    setup failure. Those leave NO row in the collector, so without this
    hook they would be invisible to compute_exit_code() and the run could
    exit 0 despite a probe having silently never run. See B2 in the M2
    milestone review.
    """
    excinfo = getattr(call, "excinfo", None)
    if excinfo is not None and not issubclass(excinfo.type, AssertionError):
        node.session._isolation_unexpected_error = True


@pytest.fixture(scope="session")
def run_config():
    return runtime.get_config()


@pytest.fixture(scope="session")
def operations():
    return runtime.get_operations()


@pytest.fixture(scope="session")
def run_dir() -> Path:
    d = runtime.get_run_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def expected_leaks():
    return runtime.get_expected()


@pytest.fixture(scope="session")
def collector(run_config, request):
    c = MatrixCollector(run_name=runtime.get_run_name(), base_url=run_config.base_url)
    request.session._isolation_collector = c
    return c


@pytest.fixture(scope="session")
def client(run_config):
    api_client = ApiClient(run_config)
    yield api_client
    api_client.close()


@pytest.fixture(scope="session", autouse=True)
def _preflight(run_config, client, collector, run_dir, expected_leaks):
    """Every actor must be able to log in, and the API must be reachable,
    before ANY probe runs. Without this, a down/misconfigured API would
    just show up as a suspicious wall of DENIED (403/404-ish) results
    that could be mistaken for "great isolation" instead of "broken run".
    """
    failures: list[str] = []
    for tenant, role, cred in run_config.all_actors():
        actor = Actor(tenant=tenant, role=role, cred=cred)
        try:
            client.token_for(actor)
        except AuthError as exc:
            failures.append(f"{actor.label}: {exc}")

    status_ok = False
    if not failures:
        try:
            resp = client.status_check()
            status_ok = resp.status_code == 200
        except Exception as exc:  # noqa: BLE001 - any failure here must abort the run clearly
            failures.append(f"/api/status unreachable: {exc}")

    if failures or not status_ok:
        collector.mark_preflight_failed()
        md_path, json_path = collector.write(run_dir, expected_leaks, run_config.excluded_findings)
        detail = "; ".join(failures) or "/api/status did not return 200"
        pytest.exit(
            f"PREFLIGHT FAILED - aborting before any probe ran: {detail}\n"
            f"(matrix written to {md_path} / {json_path} showing preflight_ok=false)",
            returncode=2,
        )
    yield


@pytest.fixture(scope="session", autouse=True)
def runtime_fixtures(run_config, client, collector, _preflight):
    """Create extra resources as each tenant's owner at session start
    (SPEC.md section 3.1: "Creates resources as Tenant 1...") so id-
    enumeration has a wider range than the static seed data, and so
    export ids (which the baseline app assigns at runtime, not via
    Flyway seed data) exist for the A-05 probes at all.

    A failed creation here is marked as a control failure (forces exit
    code 2) rather than silently producing an empty id list - a run that
    quietly skipped creating fixtures could otherwise show a deceptively
    clean matrix for the probes that depend on them.
    """
    rf = RuntimeFixtures()
    for tenant in run_config.tenants:
        owner_actor = next(a for a in actors_for_tenant(run_config, tenant) if a.role == "owner")

        extra_ids = []
        for _ in range(2):
            resp = client.call(
                "post",
                "/invoices",
                owner_actor,
                json_body={
                    "customerId": tenant.fixtures["customer_ids"][0],
                    "amount": "10.00",
                    "internalCost": "1.00",
                    "status": "draft",
                },
            )
            if resp.status_code == 200:
                extra_ids.append(resp.json()["id"])
            else:
                collector.mark_control_failed()
        rf.extra_invoice_ids[tenant.id] = extra_ids

        export_resp = client.call("post", "/invoices/export", owner_actor)
        if export_resp.status_code == 200:
            rf.export_ids[tenant.id] = [export_resp.json()["exportId"]]
        else:
            rf.export_ids[tenant.id] = []
            collector.mark_control_failed()

    return rf


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    collector = getattr(session, "_isolation_collector", None)
    if collector is None:
        # Preflight aborted before the collector fixture was even created,
        # or collection failed outright (e.g. bad config path). Nothing
        # more to write; leave whatever pytest.exit already reported.
        return
    from isolation_tester import runtime as _rt

    run_dir = _rt.get_run_dir()
    expected = _rt.get_expected()
    excluded = _rt.get_config().excluded_findings

    exit_code = collector.compute_exit_code(expected)
    if getattr(session, "_isolation_unexpected_error", False):
        exit_code = max(exit_code, 2)

    md_path, json_path = collector.write(run_dir, expected, excluded)
    session.exitstatus = exit_code
    print(f"\nisolation matrix written to:\n  {md_path}\n  {json_path}\nexit code: {session.exitstatus}")
