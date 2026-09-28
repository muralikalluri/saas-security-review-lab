"""Deliberately insecure for demonstration. Do not deploy.

Live-catalog integration test. Requires `supabase start && supabase db
reset` from targets/vibe-app/ first - skipped automatically (not failed) if
that stack isn't reachable, e.g. in CI, which only runs the pure unit tests
in test_classification.py. This is the test that actually proves the
checker's verdicts against the real, committed migrations, not synthetic
fixtures.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rls_checker import run, load_expect  # noqa: E402

DSN = "postgresql://postgres:postgres@127.0.0.1:8189/postgres"
REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_DIR = REPO_ROOT / "targets" / "vibe-app"
ALLOWLIST = Path(__file__).resolve().parents[1] / "rls-allowlist.yml"
EXPECT = Path(__file__).resolve().parents[1] / "expectations" / "vibe-app.baseline.yml"


def _db_reachable() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(DSN, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(), reason="local Supabase Postgres not reachable on 127.0.0.1:8189 - run `supabase start` in targets/vibe-app/ first"
)


def test_baseline_matches_expected_fail_set():
    findings = run(DSN, ["public"], ALLOWLIST, TARGET_DIR)
    actual_fail = {f.key() for f in findings if f.verdict == "FAIL"}
    expected = load_expect(EXPECT)
    assert actual_fail == expected


def test_classes_is_allowlisted_not_failed():
    findings = run(DSN, ["public"], ALLOWLIST, TARGET_DIR)
    classes = [f for f in findings if f.table == "classes"]
    assert classes, "expected at least one finding for public.classes"
    assert all(f.verdict != "FAIL" for f in classes)
    assert any(f.verdict == "ALLOWLISTED" for f in classes)
