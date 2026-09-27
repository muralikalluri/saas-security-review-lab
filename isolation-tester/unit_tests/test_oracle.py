"""Deliberately insecure for demonstration. Do not deploy.

Offline tests for the deny/leak classifier (isolation_tester.oracle).
These run with NO network access and NO live tenant-api - they are what
CI actually runs for this milestone. Getting this polarity wrong is the
one bug in this whole tool that would matter: it would make a leaking API
look green.
"""

import httpx

from isolation_tester.oracle import (
    Verdict,
    bola_verdict,
    enumeration_classify,
    list_verdict,
    mass_assignment_verdict,
    positive_control_verdict,
    role_verdict,
)


def _resp(status_code: int, json_body=None, text_body: str | None = None) -> httpx.Response:
    if json_body is not None:
        return httpx.Response(status_code, json=json_body)
    return httpx.Response(status_code, text=text_body or "")


class TestBolaVerdict:
    def test_403_is_denied(self):
        assert bola_verdict(_resp(403)).verdict == Verdict.DENIED

    def test_404_is_denied(self):
        assert bola_verdict(_resp(404)).verdict == Verdict.DENIED

    def test_200_is_leak(self):
        assert bola_verdict(_resp(200, json_body={"id": 1})).verdict == Verdict.LEAK

    def test_401_is_error_not_denied(self):
        c = bola_verdict(_resp(401))
        assert c.verdict == Verdict.ERROR

    def test_500_is_error_not_denied(self):
        c = bola_verdict(_resp(500))
        assert c.verdict == Verdict.ERROR


class TestListVerdict:
    def test_foreign_id_present_is_leak(self):
        resp = _resp(200, json_body=[{"id": 1}, {"id": 99}])
        c = list_verdict(resp, foreign_ids={99}, own_ids={1})
        assert c.verdict == Verdict.LEAK

    def test_only_own_rows_is_denied(self):
        resp = _resp(200, json_body=[{"id": 1}, {"id": 2}])
        c = list_verdict(resp, foreign_ids={99}, own_ids={1, 2})
        assert c.verdict == Verdict.DENIED

    def test_empty_list_is_denied(self):
        resp = _resp(200, json_body=[])
        c = list_verdict(resp, foreign_ids={99}, own_ids={1})
        assert c.verdict == Verdict.DENIED

    def test_non_list_body_is_error(self):
        resp = _resp(200, json_body={"not": "a list"})
        c = list_verdict(resp, foreign_ids={99}, own_ids={1})
        assert c.verdict == Verdict.ERROR

    def test_server_error_is_error(self):
        resp = _resp(500)
        c = list_verdict(resp, foreign_ids={99}, own_ids={1})
        assert c.verdict == Verdict.ERROR

    def test_neither_own_nor_foreign_rows_is_error(self):
        # A row set that matches neither known set can't be positively
        # classified either way - must not silently count as "denied".
        resp = _resp(200, json_body=[{"id": 12345}])
        c = list_verdict(resp, foreign_ids={99}, own_ids={1})
        assert c.verdict == Verdict.ERROR


class TestMassAssignmentVerdict:
    def test_injected_foreign_tenant_wins_is_leak(self):
        c = mass_assignment_verdict({"tenantId": "tenant-b"}, injected_tenant_id="tenant-b", caller_tenant_id="tenant-a")
        assert c.verdict == Verdict.LEAK

    def test_ignored_injection_falls_back_to_caller_is_denied(self):
        c = mass_assignment_verdict({"tenantId": "tenant-a"}, injected_tenant_id="tenant-b", caller_tenant_id="tenant-a")
        assert c.verdict == Verdict.DENIED

    def test_missing_tenant_field_is_error(self):
        c = mass_assignment_verdict({}, injected_tenant_id="tenant-b", caller_tenant_id="tenant-a")
        assert c.verdict == Verdict.ERROR

    def test_unexpected_third_tenant_is_error(self):
        c = mass_assignment_verdict({"tenantId": "tenant-c"}, injected_tenant_id="tenant-b", caller_tenant_id="tenant-a")
        assert c.verdict == Verdict.ERROR


class TestRoleVerdict:
    def test_403_is_denied(self):
        assert role_verdict(_resp(403)).verdict == Verdict.DENIED

    def test_200_is_leak(self):
        assert role_verdict(_resp(200, json_body=1)).verdict == Verdict.LEAK

    def test_401_is_error(self):
        assert role_verdict(_resp(401)).verdict == Verdict.ERROR


class TestPositiveControlVerdict:
    def test_200_is_allowed(self):
        assert positive_control_verdict(_resp(200, json_body={})).verdict == Verdict.ALLOWED

    def test_403_is_error_not_denied(self):
        # A failed positive control is a broken RUN, never "extra secure".
        assert positive_control_verdict(_resp(403)).verdict == Verdict.ERROR

    def test_404_is_error(self):
        assert positive_control_verdict(_resp(404)).verdict == Verdict.ERROR


class TestEnumerationClassify:
    def test_own_id_with_200_is_own(self):
        assert enumeration_classify(_resp(200), resource_id=1, own_ids={1}, foreign_ids_known=set()) == "own"

    def test_own_id_with_404_is_error(self):
        # Contradicts our own fixture data - the run's ground truth is wrong.
        assert enumeration_classify(_resp(404), resource_id=1, own_ids={1}, foreign_ids_known=set()) == "error"

    def test_non_own_id_denied_is_denied(self):
        assert enumeration_classify(_resp(404), resource_id=42, own_ids={1}, foreign_ids_known=set()) == "denied"

    def test_non_own_id_200_is_leak(self):
        assert enumeration_classify(_resp(200), resource_id=42, own_ids={1}, foreign_ids_known=set()) == "leak"

    def test_server_error_is_error(self):
        assert enumeration_classify(_resp(500), resource_id=42, own_ids={1}, foreign_ids_known=set()) == "error"
