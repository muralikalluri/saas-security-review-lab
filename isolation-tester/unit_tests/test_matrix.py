"""Deliberately insecure for demonstration. Do not deploy.

Offline tests for the exit-code policy in isolation_tester.matrix. This is
the second most important piece of polarity in the tool: what actually
makes CI red or green.
"""

from isolation_tester.matrix import MatrixCollector, ProbeResult


def _result(finding, verdict, probe_type="bola"):
    return ProbeResult(
        probe_id=f"p-{finding}-{verdict}",
        probe_type=probe_type,
        finding=finding,
        actor="someone@tenant",
        method="GET",
        path="/x",
        verdict=verdict,
        detail="synthetic",
    )


def test_no_leaks_no_expectations_is_exit_0():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "DENIED"))
    assert c.compute_exit_code(expected=None) == 0


def test_unexpected_leak_no_expectations_is_exit_1():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    assert c.compute_exit_code(expected=None) == 1


def test_error_always_wins_over_leak():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    c.record(_result("A-02", "ERROR"))
    assert c.compute_exit_code(expected=None) == 2
    assert c.compute_exit_code(expected={"A-01"}) == 2


def test_failed_positive_control_forces_exit_2_even_with_zero_leaks():
    c = MatrixCollector("run", "http://x")
    c.record(_result(None, "ALLOWED", probe_type="positive-control"))
    c.mark_control_failed()
    assert c.compute_exit_code(expected=None) == 2
    assert c.compute_exit_code(expected=set()) == 2


def test_failed_preflight_forces_exit_2():
    c = MatrixCollector("run", "http://x")
    c.mark_preflight_failed()
    assert c.compute_exit_code(expected=set()) == 2


def test_actual_leaks_matching_expected_set_exactly_is_exit_0():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    c.record(_result("A-02", "LEAK"))
    assert c.compute_exit_code(expected={"A-01", "A-02"}) == 0


def test_missing_expected_leak_is_a_regression_exit_1():
    # Baseline "stopped" finding A-02 - just as bad as a new leak.
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    assert c.compute_exit_code(expected={"A-01", "A-02"}) == 1


def test_extra_unexpected_leak_is_exit_1():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    c.record(_result("A-09", "LEAK"))  # not in the expected set
    assert c.compute_exit_code(expected={"A-01"}) == 1


def test_denied_rows_never_count_as_leaks():
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "DENIED"))
    assert c.leaked_findings() == set()


def test_unattributed_leak_on_a_positive_control_forces_exit_1_even_if_expected_set_matches():
    # A LEAK with finding=None (e.g. GET /customers/{id} or /invoices/search
    # leaking) has no finding id to break the expected-set equality check -
    # without a dedicated guard this would silently exit 0. See B1 in the
    # M2 milestone review.
    c = MatrixCollector("run", "http://x")
    c.record(_result("A-01", "LEAK"))
    c.record(_result(None, "LEAK", probe_type="bola"))
    assert c.compute_exit_code(expected={"A-01"}) == 1
    assert c.compute_exit_code(expected=None) == 1


def test_unattributed_leak_with_no_other_leaks_still_forces_exit_1():
    c = MatrixCollector("run", "http://x")
    c.record(_result(None, "LEAK", probe_type="list-foreign-rows"))
    assert c.compute_exit_code(expected=set()) == 1
    assert c.compute_exit_code(expected=None) == 1
