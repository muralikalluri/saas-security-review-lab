"""Deliberately insecure for demonstration. Do not deploy.

Shared "call + classify + save evidence + record + assert" runners used by
the actual pytest probe files in isolation-tester/tests/. Keeping this
logic here (rather than duplicated per test file) is what makes the
per-probe-type oracle correctness the ONE place to get right.
"""

from __future__ import annotations

from pathlib import Path

from isolation_tester.http_client import ApiClient, Actor, save_evidence
from isolation_tester.matrix import MatrixCollector, ProbeResult
from isolation_tester.oracle import (
    Classification,
    Verdict,
    bola_verdict,
    enumeration_classify,
    list_verdict,
    mass_assignment_verdict_by_visibility,
    positive_control_verdict,
    role_verdict,
)


def record_probe(
    collector: MatrixCollector,
    run_dir: Path,
    *,
    probe_id: str,
    probe_type: str,
    finding: str | None,
    actor: Actor,
    method: str,
    path: str,
    classification: Classification,
    request_headers: dict,
    request_body,
    response,
) -> ProbeResult:
    evidence_path = save_evidence(
        run_dir,
        probe_id,
        method=method,
        path=path,
        actor_label=actor.label,
        request_headers=request_headers,
        request_body=request_body,
        response=response,
    )
    result = ProbeResult(
        probe_id=probe_id,
        probe_type=probe_type,
        finding=finding,
        actor=actor.label,
        method=method,
        path=path,
        verdict=classification.verdict.value,
        detail=classification.detail,
        evidence_path=evidence_path,
    )
    collector.record(result)
    return result


def assert_not_leaked(result: ProbeResult) -> None:
    assert result.verdict not in (Verdict.LEAK.value, Verdict.ERROR.value), (
        f"{result.probe_type} probe on {result.method} {result.path} as {result.actor} "
        f"-> {result.verdict}: {result.detail}"
    )


def run_positive_control(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding_label: str,
    actor: Actor,
    method: str,
    path: str,
) -> ProbeResult:
    response = client.call(method, path, actor)
    classification = positive_control_verdict(response)
    result = record_probe(
        collector,
        run_dir,
        probe_id=f"control:{finding_label}:{actor.label}",
        probe_type="positive-control",
        finding=None,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers={},
        request_body=None,
        response=response,
    )
    if classification.verdict != Verdict.ALLOWED:
        collector.mark_control_failed()
    assert classification.verdict == Verdict.ALLOWED, (
        f"positive control failed: {actor.label} could not access their own "
        f"{method} {path}: {classification.detail}"
    )
    return result


def record_bola(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding: str | None,
    actor: Actor,
    method: str,
    path: str,
) -> ProbeResult:
    """Record a single BOLA probe result WITHOUT asserting - used both by
    the parametrized invoice/customer probes below and by the export probe
    (test_export_bola.py), whose ids are only known at runtime and so are
    looped over inside one test body instead of via parametrize.
    """
    response = client.call(method, path, actor)
    classification = bola_verdict(response)
    return record_probe(
        collector,
        run_dir,
        probe_id=f"bola:{path}:{actor.label}",
        probe_type="bola",
        finding=finding,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers={},
        request_body=None,
        response=response,
    )


def run_bola_probe(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding: str | None,
    actor: Actor,
    method: str,
    path_template: str,
    resource_id: int,
) -> ProbeResult:
    path = path_template.format(id=resource_id)
    result = record_bola(client, collector, run_dir, finding=finding, actor=actor, method=method, path=path)
    assert_not_leaked(result)
    return result


def run_list_probe(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    probe_type: str,
    finding: str | None,
    actor: Actor,
    method: str,
    path: str,
    foreign_ids,
    own_ids,
    headers: dict | None = None,
) -> ProbeResult:
    response = client.call(method, path, actor, headers=headers)
    classification = list_verdict(response, foreign_ids=foreign_ids, own_ids=own_ids)
    probe_id = f"{probe_type}:{path}:{actor.label}" + (f":spoof={headers['X-Tenant-Id']}" if headers else "")
    result = record_probe(
        collector,
        run_dir,
        probe_id=probe_id,
        probe_type=probe_type,
        finding=finding,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers=headers or {},
        request_body=None,
        response=response,
    )
    assert_not_leaked(result)
    return result


def run_mass_assignment_probe(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding: str | None,
    actor: Actor,
    method: str,
    path: str,
    body: dict,
    target_actor: Actor,
    target_list_path: str,
) -> ProbeResult:
    """target_actor: a user of the tenant the request tries to mass-assign
    the row INTO. target_list_path: e.g. "/invoices", used to check
    whether the created resource's id shows up in target_actor's OWN list
    - see mass_assignment_verdict_by_visibility for why this is a list
    membership check, not a single-resource read-back, and why it doesn't
    rely on any response DTO field.
    """
    response = client.call(method, path, actor, json_body=body)
    target_tenant_can_see_it = None
    if 200 <= response.status_code < 300:
        try:
            created_id = response.json().get("id")
        except ValueError:
            created_id = None
        list_response = client.call("get", target_list_path, target_actor)
        if created_id is not None and list_response.status_code == 200:
            try:
                target_tenant_can_see_it = created_id in {row.get("id") for row in list_response.json()}
            except ValueError:
                target_tenant_can_see_it = None
    classification = mass_assignment_verdict_by_visibility(response.status_code, target_tenant_can_see_it)
    result = record_probe(
        collector,
        run_dir,
        probe_id=f"mass-assignment:{path}:{actor.label}",
        probe_type="mass-assignment",
        finding=finding,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers={},
        request_body=body,
        response=response,
    )
    assert_not_leaked(result)
    return result


def run_id_enumeration_probe(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding: str | None,
    actor: Actor,
    method: str,
    path_template: str,
    resource_id: int,
    own_ids: set,
) -> ProbeResult:
    path = path_template.format(id=resource_id)
    response = client.call(method, path, actor)
    label = enumeration_classify(response, resource_id, own_ids=own_ids, foreign_ids_known=set())
    verdict_map = {
        "own": Verdict.ALLOWED,
        "denied": Verdict.DENIED,
        "leak": Verdict.LEAK,
        "error": Verdict.ERROR,
    }
    classification = Classification(verdict_map[label], f"id={resource_id} classified as '{label}' (status {response.status_code})")
    result = record_probe(
        collector,
        run_dir,
        probe_id=f"id-enum:{path}:{actor.label}:id={resource_id}",
        probe_type="id-enum",
        finding=finding,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers={},
        request_body=None,
        response=response,
    )
    if label == "own":
        assert classification.verdict == Verdict.ALLOWED, result.detail
    else:
        assert_not_leaked(result)
    return result


def run_role_probe(
    client: ApiClient,
    collector: MatrixCollector,
    run_dir: Path,
    *,
    finding: str | None,
    actor: Actor,
    method: str,
    path: str,
    body: dict,
) -> ProbeResult:
    response = client.call(method, path, actor, json_body=body)
    classification = role_verdict(response)
    result = record_probe(
        collector,
        run_dir,
        probe_id=f"role-restricted:{path}:{actor.label}",
        probe_type="role-restricted",
        finding=finding,
        actor=actor,
        method=method,
        path=path,
        classification=classification,
        request_headers={},
        request_body=body,
        response=response,
    )
    assert_not_leaked(result)
    return result
