"""Deliberately insecure for demonstration. Do not deploy.

Unit tests for the checker's PURE classification logic (no live Postgres
needed - see test_integration.py for the live-catalog test against a real
`supabase db reset` stack). These cover exactly the edge cases the design
review, and later a milestone review that caught real bugs in an earlier
version of this logic, called out as easy to get subtly wrong.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rls_checker import Policy, classify_open_policy, classify_table  # noqa: E402


def policy(name, cmd, qual=None, with_check=None, permissive=True, roles=("authenticated",)):
    return Policy(name=name, permissive=permissive, roles=list(roles), cmd=cmd, qual=qual, with_check=with_check)


def _grants(overrides=None):
    base = {(role, priv): False for role in ("anon", "authenticated") for priv in ("SELECT", "INSERT", "UPDATE", "DELETE")}
    base.update(overrides or {})
    return base


# Full grants for both roles on every command - the default for tests about
# POLICY logic, so the (separate, also-tested-below) grant requirement never
# interferes with what's actually being tested.
FULL_GRANTS = _grants({(role, priv): True for role in ("anon", "authenticated") for priv in ("SELECT", "INSERT", "UPDATE", "DELETE")})


# ---- classify_open_policy: the core edge-case matrix -----------------------


def test_no_policies_for_cmd_is_not_open():
    is_open, evidence = classify_open_policy([], "SELECT", FULL_GRANTS)
    assert is_open is False
    assert evidence == []


def test_single_permissive_true_select_is_open():
    policies = [policy("p1", "SELECT", qual="true")]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is True
    assert evidence == ["p1"]


def test_single_permissive_scoped_select_is_not_open():
    policies = [policy("p1", "SELECT", qual="(auth.uid() = id)")]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is False


def test_restrictive_policy_narrows_an_open_permissive_one():
    policies = [
        policy("open", "SELECT", qual="true"),
        policy("narrow", "SELECT", qual="(auth.uid() = id)", permissive=False),
    ]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is False, "a real RESTRICTIVE policy must AND against the open permissive one"


def test_restrictive_policy_that_is_itself_true_does_not_narrow_anything():
    policies = [
        policy("open", "SELECT", qual="true"),
        policy("fake_narrow", "SELECT", qual="true", permissive=False),
    ]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is True, "a RESTRICTIVE policy that is also `true` restricts nothing"


def test_restrictive_policy_scoped_to_a_different_role_does_not_narrow():
    """A milestone review caught this: a RESTRICTIVE policy only narrows the
    roles it's actually scoped to. `anon` has no restrictive policy applied
    to it here at all, so it stays wide open even though `authenticated` is
    separately narrowed - lumping "any restrictive policy on an exposed
    role" together (the earlier, buggy version) would wrongly clear this."""
    policies = [
        policy("open_for_everyone", "SELECT", qual="true", roles=("anon", "authenticated")),
        policy("narrow_authenticated_only", "SELECT", qual="(auth.uid() = id)", permissive=False, roles=("authenticated",)),
    ]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is True, "anon is still wide open; the restrictive policy never applies to anon"
    assert evidence == ["open_for_everyone"]


def test_two_permissive_policies_one_open_is_still_open():
    policies = [
        policy("scoped", "SELECT", qual="(auth.uid() = id)"),
        policy("wide_open", "SELECT", qual="true"),
    ]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is True
    assert evidence == ["wide_open"], "only the actually-open policy should be cited as evidence"


def test_update_own_row_is_not_open_for_update():
    # This is the exact shape of profiles_update_own_row - must NOT be flagged.
    policies = [policy("own_row", "UPDATE", qual="(auth.uid() = id)", with_check="(auth.uid() = id)")]
    is_open, _ = classify_open_policy(policies, "UPDATE", FULL_GRANTS)
    assert is_open is False


def test_insert_open_is_detected_via_with_check_not_qual():
    policies = [policy("open_insert", "INSERT", qual=None, with_check="true")]
    is_open, evidence = classify_open_policy(policies, "INSERT", FULL_GRANTS)
    assert is_open is True
    assert evidence == ["open_insert"]


def test_using_only_policy_opens_insert_via_with_check_fallback():
    """Postgres: WITH CHECK defaults to USING when omitted, for
    INSERT/UPDATE/ALL policies. A milestone review confirmed this live
    (an ALL policy with only `using(true)` and no with_check let INSERT
    through against a real Postgres). A checker that only reads with_check
    for INSERT would false-negative on exactly this common shape."""
    policies = [policy("using_only", "ALL", qual="true", with_check=None)]
    is_open, evidence = classify_open_policy(policies, "INSERT", FULL_GRANTS)
    assert is_open is True, "with_check falls back to qual when omitted - this IS open for INSERT"
    assert evidence == ["using_only"]


def test_restrictive_using_only_true_does_not_narrow_insert_either():
    """Same fallback rule applied to a RESTRICTIVE policy: `using(true)`
    with no with_check is *itself* wide open for INSERT too (effective
    with_check falls back to true), so it narrows nothing."""
    policies = [
        policy("open", "INSERT", qual=None, with_check="true"),
        policy("fake_narrow_all", "ALL", qual="true", with_check=None, permissive=False),
    ]
    is_open, _ = classify_open_policy(policies, "INSERT", FULL_GRANTS)
    assert is_open is True


def test_cmd_all_policy_covers_every_command():
    policies = [policy("all_open", "ALL", qual="true", with_check="true")]
    for cmd in ("SELECT", "INSERT", "UPDATE", "DELETE"):
        is_open, _ = classify_open_policy(policies, cmd, FULL_GRANTS)
        assert is_open is True, f"ALL-scoped open policy must cover {cmd}"


def test_policy_scoped_only_to_service_role_is_ignored():
    policies = [policy("service_only", "SELECT", qual="true", roles=("service_role",))]
    is_open, evidence = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is False, "service_role bypasses RLS anyway - not a PostgREST-reachable finding"


def test_policy_scoped_to_public_counts_as_exposed():
    policies = [policy("everyone", "SELECT", qual="true", roles=("public",))]
    is_open, _ = classify_open_policy(policies, "SELECT", FULL_GRANTS)
    assert is_open is True


def test_open_policy_without_the_underlying_grant_is_not_a_finding():
    """A milestone review caught this: RLS policies only narrow a privilege
    a role already holds via GRANT. A wide-open policy on a command neither
    anon nor authenticated has been GRANTed is not reachable via PostgREST
    at all - not a finding, regardless of how open the policy text is."""
    policies = [policy("wide_open", "SELECT", qual="true", roles=("anon", "authenticated"))]
    is_open, evidence = classify_open_policy(policies, "SELECT", _grants())  # no grants at all
    assert is_open is False
    assert evidence == []


def test_open_policy_is_a_finding_for_the_one_role_that_has_the_grant():
    policies = [policy("wide_open", "SELECT", qual="true", roles=("anon", "authenticated"))]
    is_open, evidence = classify_open_policy(policies, "SELECT", _grants({("authenticated", "SELECT"): True}))
    assert is_open is True
    assert evidence == ["wide_open"]


# ---- classify_table: table-level wiring, grants, allowlist ----------------


def test_rls_disabled_with_grant_is_fail():
    findings = classify_table(
        "public", "bookings", rls_enabled=False, policies=[],
        grants=_grants({("authenticated", "SELECT"): True}), allowlist={},
    )
    assert len(findings) == 1
    assert findings[0].verdict == "FAIL"
    assert findings[0].reason == "rls_disabled_with_grant"


def test_rls_disabled_without_grant_is_info_not_fail():
    findings = classify_table(
        "public", "internal_only", rls_enabled=False, policies=[], grants=_grants(), allowlist={},
    )
    assert len(findings) == 1
    assert findings[0].verdict == "INFO"


def test_rls_enabled_zero_policies_is_info_deny_all():
    findings = classify_table(
        "public", "locked_down", rls_enabled=True, policies=[],
        grants=_grants({("authenticated", "SELECT"): True}), allowlist={},
    )
    assert len(findings) == 1
    assert findings[0].verdict == "INFO"
    assert findings[0].reason == "rls_enabled_zero_policies"


def test_profiles_shape_flags_select_only_not_update():
    """The real B-04 shape: an open SELECT policy plus a properly-scoped
    UPDATE policy on the same table. Only SELECT should FAIL. Grants mirror
    the real migration: both SELECT and UPDATE are actually granted."""
    policies = [
        policy("profiles_select_any_row_b04", "SELECT", qual="true", roles=("authenticated",)),
        policy("profiles_update_own_row", "UPDATE", qual="(auth.uid() = id)", with_check="(auth.uid() = id)", roles=("authenticated",)),
    ]
    grants = _grants({("authenticated", "SELECT"): True, ("authenticated", "UPDATE"): True})
    findings = classify_table("public", "profiles", rls_enabled=True, policies=policies, grants=grants, allowlist={})
    fails = [f for f in findings if f.verdict == "FAIL"]
    assert len(fails) == 1
    assert fails[0].cmd == "SELECT"


def test_allowlisted_table_is_reported_not_silently_skipped():
    policies = [policy("classes_select_all", "SELECT", qual="true", roles=("authenticated", "anon"))]
    allowlist = {("public", "classes"): "Public class listing, intentional."}
    grants = _grants({("authenticated", "SELECT"): True, ("anon", "SELECT"): True})
    findings = classify_table("public", "classes", rls_enabled=True, policies=policies, grants=grants, allowlist=allowlist)
    assert len(findings) == 1
    assert findings[0].verdict == "ALLOWLISTED"
    assert findings[0].allowlist_reason == "Public class listing, intentional."


def test_allowlisted_rls_disabled_table_is_also_reported_not_skipped():
    allowlist = {("public", "legacy_export"): "Deprecated table, scheduled for drop."}
    findings = classify_table(
        "public", "legacy_export", rls_enabled=False, policies=[],
        grants=_grants({("anon", "SELECT"): True}), allowlist=allowlist,
    )
    assert findings[0].verdict == "ALLOWLISTED"
