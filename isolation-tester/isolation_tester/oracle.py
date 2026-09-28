"""Deliberately insecure for demonstration. Do not deploy.

The deny/leak classifier. This is the single most correctness-critical
module in the whole tool: getting the polarity wrong here means the harness
could silently report a green matrix for a leaking API. See the design
review notes in isolation-tester/README.md for the invariants this encodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

import httpx


class Verdict(str, Enum):
    DENIED = "DENIED"
    LEAK = "LEAK"
    ERROR = "ERROR"
    EXCLUDED = "EXCLUDED"
    NOT_RUN = "NOT_RUN"
    ALLOWED = "ALLOWED"  # positive controls only: the resource owner succeeded


@dataclass
class Classification:
    verdict: Verdict
    detail: str


def _is_deny_status(response: httpx.Response) -> bool:
    return response.status_code in (403, 404)


def _is_server_or_auth_error(response: httpx.Response) -> bool:
    return response.status_code == 401 or response.status_code >= 500


def positive_control_verdict(response: httpx.Response) -> Classification:
    """A resource owner accessing their own resource. Must succeed - if it
    doesn't, either the app is down/misconfigured, or (in a hypothetical
    over-aggressive fix) legitimate access got blocked along with the leak.
    Either way the whole run is untrustworthy, not "extra secure".
    """
    if 200 <= response.status_code < 300:
        return Classification(Verdict.ALLOWED, f"status {response.status_code}")
    return Classification(Verdict.ERROR, f"owner was denied their own resource: status {response.status_code}")


def bola_verdict(response: httpx.Response) -> Classification:
    """A single-resource GET/PUT against a KNOWN FOREIGN id.

    A deny (403/404) is correct isolation. Any 2xx means the caller read or
    wrote a resource that belongs to another tenant/actor - that is a leak
    by definition, regardless of what the body contains. 401/5xx is a
    harness/API error, never evidence of correct isolation.
    """
    if _is_server_or_auth_error(response):
        return Classification(Verdict.ERROR, f"unexpected status {response.status_code}")
    if _is_deny_status(response):
        return Classification(Verdict.DENIED, f"status {response.status_code}")
    if 200 <= response.status_code < 300:
        return Classification(Verdict.LEAK, f"status {response.status_code} on a foreign resource")
    return Classification(Verdict.ERROR, f"unexpected status {response.status_code}")


def list_verdict(response: httpx.Response, foreign_ids: Iterable[Any], own_ids: Iterable[Any] | None = None) -> Classification:
    """A list endpoint. Leak = any row whose id is in the known-foreign set."""
    if _is_server_or_auth_error(response) or response.status_code >= 300:
        return Classification(Verdict.ERROR, f"unexpected status {response.status_code}")
    try:
        body = response.json()
    except ValueError:
        return Classification(Verdict.ERROR, "response was not valid JSON")
    if not isinstance(body, list):
        return Classification(Verdict.ERROR, "expected a JSON array from a list endpoint")
    foreign = set(foreign_ids)
    seen_ids = {row.get("id") for row in body if isinstance(row, dict)}
    leaked = seen_ids & foreign
    if leaked:
        return Classification(Verdict.LEAK, f"foreign ids present in response: {sorted(leaked)}")
    if own_ids is not None and not (seen_ids & set(own_ids)) and seen_ids:
        # Non-empty but contains neither foreign nor known-own rows: cannot
        # positively confirm isolation, but also cannot claim a leak.
        return Classification(Verdict.ERROR, f"response contained neither known-own nor known-foreign ids: {sorted(seen_ids)}")
    return Classification(Verdict.DENIED, "no foreign ids present")


def mass_assignment_verdict_by_visibility(create_status: int, target_tenant_can_see_it: bool | None) -> Classification:
    """POST with a client-supplied tenantId. Oracle is visibility-based, NOT
    dependent on any response DTO field: after creating, check whether the
    INJECTED target tenant's own LIST of their resources now includes the
    new one. If it does, it genuinely landed in their tenant - a leak. If
    it doesn't, it did not land there, regardless of what fields a given
    DTO happens to expose.

    Deliberately uses the target's own LIST endpoint, not a single-resource
    GET by id: a single-resource GET is exactly what A-01/A-05 (BOLA) probe
    already covers, and on an API where ONLY those are still broken (A-03
    itself fixed), a GET-by-id read-back would misreport DENIED-in-A-03 as
    LEAK purely because of the OTHER finding. Checking the target's own
    list decouples this probe from that overlap.

    A 403 creating the resource at all (a role gate unrelated to tenant
    isolation - e.g. a viewer who simply isn't allowed to create anything)
    is DENIED, not ERROR: if the actor can't create the resource in the
    first place, mass-assignment is moot, and calling that an error would
    force every fixed API with any create-side role check to look
    untrustworthy. This is deliberately DTO-shape-independent: a correctly
    fixed response DTO should drop tenantId/internalCost entirely (BOPLA),
    and an oracle that required reading tenantId back out of the response
    would then misreport a correct fix as an ERROR. See the M3 milestone
    notes.
    """
    if create_status == 403:
        return Classification(Verdict.DENIED, "actor is not permitted to create this resource at all - mass-assignment is moot")
    if not (200 <= create_status < 300):
        return Classification(Verdict.ERROR, f"unexpected status {create_status} creating resource")
    if target_tenant_can_see_it is None:
        return Classification(Verdict.ERROR, "could not determine whether the injected target tenant can see the created resource")
    if target_tenant_can_see_it:
        return Classification(Verdict.LEAK, "the injected target tenant's own list includes the newly created resource")
    return Classification(Verdict.DENIED, "the injected target tenant's own list does not include the newly created resource")


def role_verdict(response: httpx.Response) -> Classification:
    """A role-restricted action attempted by a caller who should be denied."""
    if _is_server_or_auth_error(response):
        return Classification(Verdict.ERROR, f"unexpected status {response.status_code}")
    if response.status_code == 403:
        return Classification(Verdict.DENIED, "status 403")
    if 200 <= response.status_code < 300:
        return Classification(Verdict.LEAK, f"status {response.status_code} - action should have required a higher role")
    return Classification(Verdict.ERROR, f"unexpected status {response.status_code}")


def enumeration_classify(response: httpx.Response, resource_id: Any, own_ids: set, foreign_ids_known: set) -> str:
    """Classify one id probed during id-enumeration as own/foreign/nonexistent/error,
    without assuming the id is in either known set (it may be an id created
    fresh this run, or genuinely absent).
    """
    if _is_server_or_auth_error(response):
        return "error"
    if resource_id in own_ids:
        return "own" if 200 <= response.status_code < 300 else "error"
    if _is_deny_status(response):
        return "denied"
    if 200 <= response.status_code < 300:
        return "leak"
    return "error"
