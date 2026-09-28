#!/usr/bin/env python3
"""Deliberately insecure for demonstration. Do not deploy.

CI-safe regression gate for the tools that don't need a live Supabase
stack (gitleaks, semgrep). Per the design review for this milestone: a
baseline scan finding real, seeded secrets/patterns is SUPPOSED to happen -
CI must not gate on "zero findings" (meaningless for an intentionally
vulnerable target) - it gates on "exactly the expected finding set", so a
fix that silently closes a finding, or a genuinely new unexpected one, both
fail the build.

The RLS checker's own baseline check (needs `supabase start` +
`supabase db reset` first) is intentionally NOT run here - see
scanners/rls-checker/tests/test_integration.py, which self-skips when no
live Postgres is reachable. Run it locally; CI only runs its pure unit
tests (test_classification.py). See scanners/README.md for the RLS checker
section.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNERS = REPO_ROOT / "scanners"

EXPECTED_GITLEAKS = {
    ("jwt", "targets/vibe-app/.env", 18),
    ("jwt", "targets/vibe-app/.env", 23),
    ("secret-named-key-literal-value", "targets/vibe-app/.env", 27),
    ("secret-named-key-literal-value", "targets/vibe-app/.env", 28),
    ("secret-named-key-literal-value", "targets/tenant-api/src/main/resources/application.yml", 42),
    ("secret-named-const-literal-value", "targets/vibe-app/lib/stripe.ts", 11),
    ("spring-default-secret-fallback", "targets/tenant-api/src/main/resources/application.yml", 12),
}

EXPECTED_SEMGREP = {
    ("b01-nextpublic-service-role-key", "targets/vibe-app/components/AdminUserList.tsx", 19),
    ("b05-missing-ownership-check", "targets/vibe-app/app/api/admin/grant-credits/route.ts", 31),
    ("b05-missing-ownership-check", "targets/vibe-app/app/api/bookings/[id]/cancel/route.ts", 19),
    ("b05-missing-ownership-check", "targets/vibe-app/app/api/bookings/route.ts", 44),
    ("b05-missing-ownership-check", "targets/vibe-app/app/api/stripe/webhook/route.ts", 31),
}

# semgrep --test has a path-relation quirk with this repo's layout (fixtures
# live in semgrep-rules/fixtures/, not .../tests/ - see scanners/README.md),
# so fixtures are verified here instead: exactly the `ruleid:`-annotated
# lines below must fire, and nothing else in the fixture files.
EXPECTED_FIXTURE_HITS = {
    ("b01-nextpublic-service-role-key", "fixtures/b01.ts", 6),
    ("b01-nextpublic-service-role-key", "fixtures/b01.ts", 12),
    ("b05-missing-ownership-check", "fixtures/b05.ts", 6),
    ("b05-missing-ownership-check", "fixtures/b05.ts", 12),
}

EXPECTED_ATTRIBUTION_COUNTS = {"harness": 7, "tool": 6, "manual": 12}


def _run_tool_writing_report(cmd: list[str], out_path: Path, allowed_returncodes: set[int]) -> None:
    """Deletes out_path first and requires it to exist afterwards - a tool
    that errors out (bad config, a removed flag) must not leave a STALE
    report on disk silently read as if it were fresh."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode not in allowed_returncodes:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"{cmd[0]} exited {proc.returncode} (not in {allowed_returncodes}) - treating as a tool failure, not '0 findings'")
    if not out_path.exists():
        raise SystemExit(f"{cmd[0]} did not (re)write {out_path} - stale-report check failed")


def run_gitleaks() -> set[tuple[str, str, int]]:
    out_path = SCANNERS / "results" / "gitleaks" / "report.json"
    _run_tool_writing_report(
        [
            "gitleaks", "git", "--no-banner",
            "--config", str(SCANNERS / "gitleaks" / "gitleaks.toml"),
            "--report-format", "json", "--report-path", str(out_path),
        ],
        out_path,
        allowed_returncodes={0, 1},  # 1 = leaks found, expected on this baseline
    )
    data = json.loads(out_path.read_text()) if out_path.stat().st_size else []
    return {(f["RuleID"], f["File"], f["StartLine"]) for f in data}


def _semgrep_scan(config: Path, targets: list[str]) -> dict:
    proc = subprocess.run(
        ["semgrep", "scan", "--config", str(config), *targets, "--no-git-ignore", "--json"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode not in (0, 1):  # 1 = findings, expected
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"semgrep exited {proc.returncode} - treating as a tool failure, not '0 findings'")
    return json.loads(proc.stdout)


def run_semgrep() -> set[tuple[str, str, int]]:
    out_path = SCANNERS / "results" / "semgrep" / "vibe-app.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)
    config = SCANNERS / "semgrep-rules" / "vibe-app.yml"
    data = _semgrep_scan(config, ["targets/vibe-app/app", "targets/vibe-app/components", "targets/vibe-app/lib"])
    out_path.write_text(json.dumps(data, indent=2))
    if not out_path.exists():
        raise SystemExit(f"semgrep did not write {out_path} - stale-report check failed")
    rule_prefix = "scanners.semgrep-rules."
    return {
        (r["check_id"].removeprefix(rule_prefix), r["path"], r["start"]["line"])
        for r in data.get("results", [])
    }


def run_semgrep_fixtures() -> set[tuple[str, str, int]]:
    config = SCANNERS / "semgrep-rules" / "vibe-app.yml"
    data = _semgrep_scan(config, ["scanners/semgrep-rules/fixtures"])
    rule_prefix = "scanners.semgrep-rules."
    return {
        (r["check_id"].removeprefix(rule_prefix), f"fixtures/{Path(r['path']).name}", r["start"]["line"])
        for r in data.get("results", [])
    }


def run_attribution() -> dict[str, int]:
    proc = subprocess.run(
        [sys.executable, str(SCANNERS / "attribution" / "build_attribution.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        raise SystemExit("build_attribution.py failed")
    attribution = json.loads((SCANNERS / "results" / "attribution.json").read_text())
    counts: dict[str, int] = {}
    for a in attribution.values():
        counts[a["method"]] = counts.get(a["method"], 0) + 1
    return counts


def main() -> int:
    ok = True

    actual_gitleaks = run_gitleaks()
    if actual_gitleaks != EXPECTED_GITLEAKS:
        ok = False
        print("MISMATCH gitleaks:")
        print("  missing:", sorted(EXPECTED_GITLEAKS - actual_gitleaks))
        print("  unexpected:", sorted(actual_gitleaks - EXPECTED_GITLEAKS))
    else:
        print(f"OK gitleaks: {len(actual_gitleaks)} findings match expected set")

    actual_semgrep = run_semgrep()
    if actual_semgrep != EXPECTED_SEMGREP:
        ok = False
        print("MISMATCH semgrep:")
        print("  missing:", sorted(EXPECTED_SEMGREP - actual_semgrep))
        print("  unexpected:", sorted(actual_semgrep - EXPECTED_SEMGREP))
    else:
        print(f"OK semgrep: {len(actual_semgrep)} findings match expected set")

    actual_fixtures = run_semgrep_fixtures()
    if actual_fixtures != EXPECTED_FIXTURE_HITS:
        ok = False
        print("MISMATCH semgrep fixtures:")
        print("  missing:", sorted(EXPECTED_FIXTURE_HITS - actual_fixtures))
        print("  unexpected:", sorted(actual_fixtures - EXPECTED_FIXTURE_HITS))
    else:
        print(f"OK semgrep fixtures: {len(actual_fixtures)} hits match the ruleid: annotations exactly")

    # Attribution's tool-derived counts depend on rls-checker's saved output
    # too (scanners/results/rls-checker/vibe-app/rls-matrix.json) - committed
    # from the last local run against a live `supabase db reset` stack.
    # CI checks gitleaks/semgrep freshly above, then re-derives attribution
    # from whatever's currently on disk.
    counts = run_attribution()
    if counts != EXPECTED_ATTRIBUTION_COUNTS:
        ok = False
        print(f"MISMATCH attribution counts: expected {EXPECTED_ATTRIBUTION_COUNTS}, got {counts}")
    else:
        print(f"OK attribution: {counts}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
