#!/usr/bin/env python3
"""Deliberately insecure for demonstration. Do not deploy.

Supabase RLS checker (SPEC.md section 3/6, M5). Finds B-03 and B-04 the same
way a real reviewer would: by asking Postgres's own system catalogs what a
table's actual row-level-security posture is, NOT by parsing the migration
SQL as text.

Why the live catalog and not regex over the .sql files:
  - Tables are created in one migration and RLS is enabled/policies added in
    a later one - correctness requires the FINAL replayed state, not any
    single file.
  - `alter table only`, quoted/case-sensitive identifiers, `disable row
    level security`, `drop policy`, and dynamic SQL all defeat a regex.
  - B-03 (RLS never enabled at all) is an absence - you cannot regex-prove a
    statement was never run anywhere in the migration history.
Run `supabase db reset` first so the catalog exactly reflects the committed
migrations (no dashboard-console drift). This checker only ever reads
pg_catalog; it never touches migration files except to attach a best-effort
file:line evidence pointer after a verdict has already been reached from the
catalog - the lookup never decides a finding, only illustrates it.

Classification (per table, and per SQL command SELECT/INSERT/UPDATE/DELETE,
evaluated separately for the `anon` and `authenticated` roles - see
classify_open_policy's docstring for why per-role, not lumped together):
  - RLS disabled + a grant to anon/authenticated on ANY of
    SELECT/INSERT/UPDATE/DELETE  -> FAIL "rls_disabled_with_grant" (B-03).
  - RLS disabled, no such grant                -> INFO (not exposed).
  - RLS enabled, zero policies                 -> INFO (deny-all default).
  - RLS enabled: for a role that actually holds the base GRANT for this
    command (a policy narrows a privilege the role already has - it can
    never substitute for a missing GRANT), gather every PERMISSIVE policy
    scoped to that role (or to `public`) that applies to this cmd.
    Permissive policies OR together, so a single one whose qual (or
    effective with_check, for INSERT/UPDATE/ALL - Postgres falls back to
    qual when with_check is omitted, see Policy.effective_with_check)
    deparses to exactly "true" opens the command for that role UNLESS a
    RESTRICTIVE policy scoped to that SAME role actually narrows it (i.e.
    is not itself "true") - restrictive policies AND together with the
    permissive OR result. -> FAIL "open_policy" (B-04) if open and
    unnarrowed for at least one role, else PASS.
  - A (schema, table) pair listed in rls-allowlist.yml is reported as
    ALLOWLISTED instead of FAIL, with the committed reason attached - never
    silently skipped.

Known false negatives (documented, not fixed - out of scope for this lab):
  `using (1=1)` or any non-literal tautology (only the literal `true` is
  detected); views (RLS does not apply to a view unless the base table has
  it and the view is security_invoker); SECURITY DEFINER functions/RPCs;
  storage bucket policies (storage.objects - B-09 is proven manually, see
  targets/vibe-app/exploits/B-09-*.sh, not by this checker).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS = ("SELECT", "INSERT", "UPDATE", "DELETE")
PRIV_BY_COMMAND = {"SELECT": "SELECT", "INSERT": "INSERT", "UPDATE": "UPDATE", "DELETE": "DELETE"}


@dataclass
class Policy:
    name: str
    permissive: bool  # True = PERMISSIVE, False = RESTRICTIVE
    roles: list[str]
    cmd: str  # one of SELECT/INSERT/UPDATE/DELETE/ALL
    qual: Optional[str]
    with_check: Optional[str]

    def applies_to(self, cmd: str) -> bool:
        return self.cmd == "ALL" or self.cmd == cmd

    def scoped_to_role(self, role: str) -> bool:
        return role in self.roles or "public" in self.roles

    def effective_with_check(self) -> Optional[str]:
        """Postgres: if a policy has no WITH CHECK, USING doubles as the
        WITH CHECK for INSERT/UPDATE/ALL (CREATE POLICY docs) - confirmed
        live: an ALL policy with only `using(true)` and no with_check lets
        INSERT through. Getting this wrong is a false negative: a checker
        that only reads with_check for INSERT would miss exactly that
        common "using(true), no explicit with_check" shape."""
        return self.with_check if self.with_check is not None else self.qual

    def is_open_for(self, cmd: str) -> bool:
        """True if this policy's relevant clause deparses to exactly `true`
        for the given command (see PRIV_BY_COMMAND / module docstring)."""
        if cmd in ("SELECT", "DELETE"):
            return self.qual == "true"
        if cmd == "INSERT":
            return self.effective_with_check() == "true"
        # UPDATE / ALL: either clause being wide open exposes something.
        return self.qual == "true" or self.effective_with_check() == "true"


@dataclass
class TableFinding:
    schema: str
    table: str
    rls_enabled: bool
    verdict: str  # FAIL | INFO | ALLOWLISTED
    reason: str
    detail: str
    cmd: Optional[str] = None
    evidence_policies: list[str] = field(default_factory=list)
    allowlist_reason: Optional[str] = None
    file_evidence: Optional[str] = None

    def key(self) -> tuple:
        return (self.schema, self.table, self.cmd)


def load_allowlist(path: Path) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    out = {}
    for entry in data.get("allowlist", []):
        out[(entry["schema"], entry["table"])] = entry["reason"]
    return out


def fetch_tables(conn, schemas: list[str]) -> list[tuple[str, str, bool, int]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select n.nspname, c.relname, c.relrowsecurity, c.oid::int
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where c.relkind in ('r', 'p')
              and n.nspname = any(%s)
            order by n.nspname, c.relname
            """,
            (schemas,),
        )
        return cur.fetchall()


def fetch_policies(conn, schema: str, table: str) -> list[Policy]:
    with conn.cursor() as cur:
        cur.execute(
            """
            select policyname, permissive, roles::text[], cmd, qual, with_check
            from pg_policies
            where schemaname = %s and tablename = %s
            """,
            (schema, table),
        )
        rows = cur.fetchall()
    return [
        Policy(
            name=name,
            permissive=(permissive == "PERMISSIVE"),
            roles=list(roles),
            cmd=cmd,
            qual=qual,
            with_check=with_check,
        )
        for name, permissive, roles, cmd, qual, with_check in rows
    ]


def fetch_grants(conn, oid: int) -> dict[str, bool]:
    grants = {}
    with conn.cursor() as cur:
        for role in ("anon", "authenticated"):
            for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                cur.execute("select has_table_privilege(%s, %s, %s)", (role, oid, priv))
                grants[(role, priv)] = cur.fetchone()[0]
    return grants


def classify_open_policy(
    policies: list[Policy], cmd: str, grants: dict[tuple[str, str], bool]
) -> tuple[bool, list[str]]:
    """Pure logic, no DB access - the piece with real edge cases, tested in
    isolation by tests/test_classification.py.

    Evaluated PER ROLE, not once for "any exposed role" lumped together:
    Postgres evaluates a role's effective policy set as (OR of PERMISSIVE
    policies scoped to THAT role) AND (AND of RESTRICTIVE policies scoped to
    THAT role) - a restrictive policy scoped only to `authenticated` does
    nothing to narrow what `anon` can see, and vice versa. `public` in a
    policy's roles applies to both.

    Also requires the role to actually hold the base table/column privilege
    for this command (`grants`): RLS policies only ever narrow what a role
    can already do via GRANT - a wide-open policy on a command the role has
    no GRANT for is not reachable via PostgREST at all, so it isn't a
    finding.
    """
    priv = PRIV_BY_COMMAND[cmd]
    applicable = [p for p in policies if p.applies_to(cmd)]

    open_evidence: list[str] = []
    for role in ("anon", "authenticated"):
        if not grants.get((role, priv), False):
            continue
        role_applicable = [p for p in applicable if p.scoped_to_role(role)]
        permissive = [p for p in role_applicable if p.permissive]
        restrictive = [p for p in role_applicable if not p.permissive]

        open_permissive = [p for p in permissive if p.is_open_for(cmd)]
        if not open_permissive:
            continue

        # A restrictive policy ANDs with the permissive OR-result for THIS
        # role. It only narrows anything if it is not ITSELF wide open.
        narrowing_restrictive = [p for p in restrictive if not p.is_open_for(cmd)]
        if narrowing_restrictive:
            continue

        for p in open_permissive:
            if p.name not in open_evidence:
                open_evidence.append(p.name)

    return (len(open_evidence) > 0), open_evidence


def classify_table(
    schema: str,
    table: str,
    rls_enabled: bool,
    policies: list[Policy],
    grants: dict[tuple[str, str], bool],
    allowlist: dict[tuple[str, str], str],
) -> list[TableFinding]:
    allow_reason = allowlist.get((schema, table))

    if not rls_enabled:
        granted_to = [f"{role}:{priv}" for (role, priv), ok in grants.items() if ok]
        if granted_to:
            verdict = "ALLOWLISTED" if allow_reason else "FAIL"
            return [
                TableFinding(
                    schema=schema,
                    table=table,
                    rls_enabled=False,
                    verdict=verdict,
                    reason="rls_disabled_with_grant",
                    detail=f"RLS is not enabled and {', '.join(sorted(granted_to))} is granted - "
                    "any row is reachable by that role, for that operation, with no policy at all.",
                    allowlist_reason=allow_reason,
                )
            ]
        return [
            TableFinding(
                schema=schema,
                table=table,
                rls_enabled=False,
                verdict="INFO",
                reason="rls_disabled_no_grant",
                detail="RLS is not enabled, but anon/authenticated have no grants on this table either "
                "(not reachable via PostgREST as those roles).",
            )
        ]

    if not policies:
        return [
            TableFinding(
                schema=schema,
                table=table,
                rls_enabled=True,
                verdict="INFO",
                reason="rls_enabled_zero_policies",
                detail="RLS is enabled with zero policies - this is Postgres's default-deny; "
                "anon/authenticated cannot reach any row via PostgREST regardless of grants.",
            )
        ]

    findings = []
    for cmd in COMMANDS:
        is_open, evidence = classify_open_policy(policies, cmd, grants)
        if not is_open:
            continue
        verdict = "ALLOWLISTED" if allow_reason else "FAIL"
        findings.append(
            TableFinding(
                schema=schema,
                table=table,
                rls_enabled=True,
                verdict=verdict,
                reason="open_policy",
                cmd=cmd,
                detail=f"A PERMISSIVE policy for {cmd} deparses to exactly `true` and no RESTRICTIVE "
                f"policy narrows it - every row is reachable by {cmd} for anon/authenticated.",
                evidence_policies=evidence,
                allowlist_reason=allow_reason,
            )
        )
    if not findings:
        return [
            TableFinding(
                schema=schema,
                table=table,
                rls_enabled=True,
                verdict="INFO",
                reason="rls_enabled_scoped",
                detail="RLS is enabled and every applicable policy is scoped (no bare `using (true)` "
                "left unnarrowed for any command).",
            )
        ]
    return findings


MIGRATIONS_GLOB = "supabase/migrations/*.sql"


def attach_file_evidence(target_dir: Path, finding: TableFinding) -> None:
    needle_table = re.compile(rf"\b{re.escape(finding.table)}\b")
    needle_policy = (
        re.compile("|".join(re.escape(p) for p in finding.evidence_policies))
        if finding.evidence_policies
        else None
    )
    for path in sorted(target_dir.glob(MIGRATIONS_GLOB)):
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines, start=1):
            if needle_policy and needle_policy.search(line):
                finding.file_evidence = f"{path.relative_to(REPO_ROOT)}:{i}"
                return
        for i, line in enumerate(lines, start=1):
            if needle_table.search(line) and "table" in line.lower():
                finding.file_evidence = f"{path.relative_to(REPO_ROOT)}:{i}"
                return
    return


def run(dsn: str, schemas: list[str], allowlist_path: Path, target_dir: Path) -> list[TableFinding]:
    import psycopg2

    allowlist = load_allowlist(allowlist_path)
    findings: list[TableFinding] = []
    with psycopg2.connect(dsn) as conn:
        conn.set_session(readonly=True, autocommit=True)
        for schema, table, rls_enabled, oid in fetch_tables(conn, schemas):
            policies = fetch_policies(conn, schema, table)
            grants = fetch_grants(conn, oid)
            for f in classify_table(schema, table, rls_enabled, policies, grants, allowlist):
                attach_file_evidence(target_dir, f)
                findings.append(f)
    return findings


def render_markdown(findings: list[TableFinding], dsn_display: str, run_name: str) -> str:
    lines = [
        "# Supabase RLS matrix",
        "",
        "> Deliberately insecure for demonstration. Do not deploy. Run locally only.",
        "",
        f"- Run: `{run_name}`",
        f"- Target: `{dsn_display}`",
        f"- Started: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This file, its sibling `rls-matrix.json`, are generated by `python rls_checker.py` "
        "against the live Postgres catalog after `supabase db reset` - never hand-edited "
        "(CLAUDE.md).",
        "",
        "| Schema.Table | Cmd | Verdict | Reason | Detail | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings:
        cmd = f.cmd or "-"
        detail = f.detail
        if f.allowlist_reason:
            detail += f" Allowlisted: {f.allowlist_reason}"
        evidence = f.file_evidence or "-"
        lines.append(f"| `{f.schema}.{f.table}` | {cmd} | {f.verdict} | {f.reason} | {detail} | {evidence} |")
    return "\n".join(lines) + "\n"


def to_json(findings: list[TableFinding]) -> list[dict]:
    return [
        {
            "schema": f.schema,
            "table": f.table,
            "cmd": f.cmd,
            "rls_enabled": f.rls_enabled,
            "verdict": f.verdict,
            "reason": f.reason,
            "detail": f.detail,
            "evidence_policies": f.evidence_policies,
            "allowlist_reason": f.allowlist_reason,
            "file_evidence": f.file_evidence,
        }
        for f in findings
    ]


def load_expect(path: Optional[Path]) -> Optional[set[tuple]]:
    if not path:
        return None
    data = yaml.safe_load(path.read_text()) or {}
    return {(e["schema"], e["table"], e.get("cmd")) for e in data.get("expected_fail", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", default=os.environ.get(
        "RLS_CHECKER_DSN", "postgresql://postgres:postgres@127.0.0.1:8189/postgres"
    ))
    parser.add_argument("--schemas", nargs="+", default=["public"])
    parser.add_argument("--allowlist", type=Path, default=Path(__file__).parent / "rls-allowlist.yml")
    parser.add_argument("--target-dir", type=Path, default=REPO_ROOT / "targets" / "vibe-app")
    parser.add_argument("--run-name", default="vibe-app")
    parser.add_argument("--expect", type=Path, default=None)
    parser.add_argument(
        "--out-dir", type=Path, default=REPO_ROOT / "scanners" / "results" / "rls-checker"
    )
    args = parser.parse_args()

    findings = run(args.dsn, args.schemas, args.allowlist, args.target_dir)

    out_dir = args.out_dir / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    dsn_display = re.sub(r"://[^@]+@", "://***@", args.dsn)
    (out_dir / "rls-matrix.md").write_text(render_markdown(findings, dsn_display, args.run_name))
    (out_dir / "rls-matrix.json").write_text(json.dumps(to_json(findings), indent=2) + "\n")
    print(f"RLS matrix written to:\n  {out_dir / 'rls-matrix.md'}\n  {out_dir / 'rls-matrix.json'}")

    actual_fail = {f.key() for f in findings if f.verdict == "FAIL"}
    for f in findings:
        marker = {"FAIL": "FAIL", "ALLOWLISTED": "allowlisted", "INFO": "info"}[f.verdict]
        print(f"  [{marker}] {f.schema}.{f.table} {f.cmd or ''} - {f.reason}")

    expect = load_expect(args.expect)
    if expect is None:
        exit_code = 0 if not actual_fail else 1
    else:
        exit_code = 0 if actual_fail == expect else 1
        if actual_fail != expect:
            print(f"\nMISMATCH vs --expect:\n  expected: {sorted(expect)}\n  actual:   {sorted(actual_fail)}")

    print(f"\nexit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
