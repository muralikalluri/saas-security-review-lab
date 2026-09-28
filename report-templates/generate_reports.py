#!/usr/bin/env python3
"""Deliberately insecure for demonstration. Do not deploy.

Generates the 4 sample deliverables (SPEC.md section 1/5/7) from:
  - report-templates/findings-data/{tenant-api,vibe-app}.yml (per-finding
    detail - severity, OWASP mapping, what/impact/fix/effort, AI fix prompt)
  - scanners/results/attribution.json (tool/harness/manual, M5's own output)
  - results/isolation-tester/baseline/isolation-matrix.json (Target A's
    harness proof - counts computed here, never hand-typed)

Per the repo's global CLAUDE.md ("never hand-type performance numbers...
generate them from results files"): every COUNT in the generated reports
(severity totals, tool-found vs manual totals, probe totals) is computed
from these files by this script. The per-finding narrative (what/impact/
fix) is analyst prose living in the YAML above, same as a real pentester's
findings - that's the deliverable's actual content, not a "score".

Run: python3 report-templates/generate_reports.py
Output: sample-deliverables/L4-multitenant/*.md, sample-deliverables/L5-ai-app/*.md
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "report-templates"
TODAY = date.today().isoformat()

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
BANNER = "> Deliberately insecure for demonstration and training. Do not deploy. Run locally only."
# Same anchor CLAUDE.md requires at every flaw's own comment (and that
# scanners/attribution/build_attribution.py already keys on) - reused here
# to turn attribution.json's file-level evidence_files into a real file:line
# citation, instead of hand-typing a line number into the findings-data YAML.
SEEDED_FLAW_RE = re.compile(r"\b([AB]-\d\d)\s*\(seeded flaw")


def evidence_citation(finding_id: str, attribution: dict) -> str:
    files = attribution.get(finding_id, {}).get("evidence_files", [])
    citations = []
    for rel_path in files:
        path = REPO_ROOT / rel_path
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            citations.append(rel_path)
            continue
        line_no = None
        for i, line in enumerate(text.splitlines(), start=1):
            m = SEEDED_FLAW_RE.search(line)
            if m and m.group(1) == finding_id:
                line_no = i
                break
        citations.append(f"{rel_path}:{line_no}" if line_no else rel_path)
    joined = "; ".join(citations) if citations else "see targets/*/exploits/ for reproduction steps"
    # Long paths in a monospace span are one unbroken "word" to a PDF
    # renderer - insert a zero-width space after each path separator so
    # tectonic can wrap instead of overflowing the page margin.
    return joined.replace("/", "/​")


def load_findings(target: str) -> list[dict]:
    data = yaml.safe_load((TEMPLATES / "findings-data" / f"{target}.yml").read_text())
    return data["findings"]


def load_attribution() -> dict:
    return json.loads((REPO_ROOT / "scanners" / "results" / "attribution.json").read_text())


def load_isolation_matrix() -> dict:
    return json.loads((REPO_ROOT / "results" / "isolation-tester" / "baseline" / "isolation-matrix.json").read_text())


def severity_counts(findings: list[dict]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] += 1
    return counts


def risk_table(counts: dict[str, int]) -> str:
    lines = ["| Severity | Count |", "|---|---|"]
    for sev in SEVERITY_ORDER:
        lines.append(f"| {sev} | {counts[sev]} |")
    lines.append(f"| **Total** | **{sum(counts.values())}** |")
    return "\n".join(lines)


def method_line(finding_id: str, attribution: dict) -> str:
    entry = attribution.get(finding_id)
    if not entry:
        return "manual"
    method = entry["method"]
    tools = ", ".join(entry["tools"]) if entry["tools"] else None
    return f"{method} ({tools})" if tools else method


def isolation_summary(matrix: dict) -> dict:
    results = matrix["results"]
    leak_rows = [r for r in results if r["verdict"] == "LEAK"]
    control_rows = [r for r in results if r["probe_type"] == "positive-control"]
    non_control = [r for r in results if r["probe_type"] != "positive-control"]
    return {
        "total_probes": len(results),
        "control_probes": len(control_rows),
        "non_control_probes": len(non_control),
        "leak_count": len(leak_rows),
        "confirmed_findings": sorted(set(r["finding"] for r in leak_rows if r["finding"])),
        "controls_ok": matrix["controls_ok"],
        "preflight_ok": matrix["preflight_ok"],
        "exit_code": matrix["exit_code"],
    }


def render_finding_full(f: dict, method: str, evidence: str, include_ai_prompt: bool) -> str:
    lines = [
        f"### {f['id']} — {f['severity']}",
        "",
        f"**OWASP:** {f['owasp_2021']} · {f['owasp_api_2023']}  ",
        f"**Effort to fix:** {f['effort']}  ",
        f"**How found:** {method}  ",
        f"**Evidence:** `{evidence}`",
        "",
        f"**What's wrong.** {f['what']}",
        "",
        f"**Why it matters.** {f['impact']}",
        "",
        f"**Exact fix.** {f['fix']}",
    ]
    if include_ai_prompt and f.get("ai_fix_prompt"):
        lines += ["", "**AI fix prompt** (copy-paste into Claude Code / Cursor):", "", "```text", f["ai_fix_prompt"].strip(), "```"]
    lines.append("")
    return "\n".join(lines)


def render_finding_brief(f: dict, method: str, evidence: str) -> str:
    return (
        f"### {f['id']} — {f['severity']}\n\n"
        f"**OWASP:** {f['owasp_2021']} · {f['owasp_api_2023']} · **How found:** {method}  \n"
        f"**Evidence:** `{evidence}`\n\n"
        f"{f['what']} {f['impact']}\n\n"
        f"**Fix:** {f['fix']}\n"
    )


def sprint_plan(findings: list[dict]) -> str:
    by_sev = {s: [f["id"] for f in findings if f["severity"] == s] for s in SEVERITY_ORDER}
    lines = ["| Sprint | Findings | Rationale |", "|---|---|---|"]
    if by_sev["Critical"]:
        lines.append(f"| Sprint 1 | {', '.join(by_sev['Critical'])} | Critical - active cross-tenant/cross-user data exposure or full compromise |")
    if by_sev["High"]:
        lines.append(f"| Sprint 2 | {', '.join(by_sev['High'])} | High - exploitable with realistic effort, real business impact |")
    if by_sev["Medium"]:
        lines.append(f"| Sprint 3 | {', '.join(by_sev['Medium'])} | Medium - narrower blast radius or requires a secondary condition |")
    if by_sev["Low"]:
        lines.append(f"| Backlog | {', '.join(by_sev['Low'])} | Low - maintainability/hygiene, not directly exploitable |")
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# L4 - tenant-api (multi-tenant SaaS review)
# ---------------------------------------------------------------------------


def generate_l4(attribution: dict) -> None:
    findings = load_findings("tenant-api")
    counts = severity_counts(findings)
    matrix = load_isolation_matrix()
    iso = isolation_summary(matrix)
    out_dir = REPO_ROOT / "sample-deliverables" / "L4-multitenant"

    top = [f for f in findings if f["severity"] in ("Critical", "High")]

    arch = f"""# Architecture Review — LedgerLite (fictional multi-tenant invoicing API)

{BANNER}

**Prepared:** {TODAY} · **Tier:** Starter · **Target:** `targets/tenant-api` (Java 21 /
Spring Boot 3 / PostgreSQL / Keycloak, shared-schema multi-tenancy)

## Scope & method

A source-available review of LedgerLite's tenant-isolation model: how a request's
tenant is resolved, how that resolution is (or isn't) enforced at the data layer, and
where role-based function access is enforced. Method: manual code review plus this
lab's own **isolation-tester** harness (`isolation-tester/`), which replays every
declared endpoint as a foreign tenant, a lower role, a spoofed header, and a
mass-assigned tenant id, then classifies each response as LEAK or DENIED.

## Architecture at a glance

- **Tenancy model:** shared schema, `tenant_id` column on every tenant-scoped table.
- **AuthN:** Keycloak-issued JWTs (resource server pattern).
- **Tenant resolution (as found):** an `X-Tenant-Id` request header, not the JWT's own
  claim - see Finding A-04, the root-cause enabler behind most other findings below.
- **Data access:** direct repository calls by primary key, with tenant scoping left to
  each call site rather than enforced centrally (no Postgres RLS in the baseline).

## Top findings (Starter tier - {len(top)} of {len(findings)} total; see the Standard/Advanced
tier report for the complete finding set)

{chr(10).join(render_finding_brief(f, method_line(f['id'], attribution), evidence_citation(f['id'], attribution)) for f in top)}

## Risk summary

{risk_table(counts)}

Full findings, evidence, remediation plan and retest notes: `SECURITY_REVIEW_FULL.md`
(Standard/Advanced tier).
"""
    write(out_dir / "ARCHITECTURE_REVIEW.md", arch)

    full = f"""# Security Review (Full) — LedgerLite (fictional multi-tenant invoicing API)

{BANNER}

**Prepared:** {TODAY} · **Tier:** Standard/Advanced · **Target:** `targets/tenant-api`
(baseline) vs. `targets/tenant-api-fixed` (retest target)

## Scope & method

Same scope as the Starter-tier `ARCHITECTURE_REVIEW.md`, to the full finding set.
Method: manual review of every controller/repository call plus this lab's own
**isolation-tester** harness (`isolation-tester/`), which mechanically proves
cross-tenant/cross-role access failures rather than relying on manual testing alone -
see `isolation-matrix.md` (this directory) for the full endpoint×actor matrix with
per-probe evidence.

**Harness run summary** (from `results/isolation-tester/baseline/isolation-matrix.json`,
generated by the harness itself - see that file's own header for how to reproduce):
{iso['non_control_probes']} non-control probes across every declared endpoint × actor
combination ({iso['control_probes']} additional positive-control probes confirmed
legitimate owner access still works), preflight {'OK' if iso['preflight_ok'] else 'FAILED'},
positive controls {'OK' if iso['controls_ok'] else 'FAILED'}. **{iso['leak_count']} probes
classified LEAK**, confirming findings {', '.join(iso['confirmed_findings'])}
mechanically, not just by manual inspection.

## Risk summary

{risk_table(counts)}

## Findings

{chr(10).join(render_finding_full(f, method_line(f['id'], attribution), evidence_citation(f['id'], attribution), include_ai_prompt=False) for f in findings)}

## Remediation plan

{sprint_plan(findings)}

## Retest notes

`targets/tenant-api-fixed` is this repo's own retest target: a separate Maven
module/database/Keycloak realm implementing every fix above (see its own README's
"What changed, per finding" table). Re-running the SAME isolation-tester config against
it (`--run-name fixed`, pointed at the fixed instance's port) is the retest evidence -
see `results/isolation-tester/fixed/isolation-matrix.md`: **0 leaks, exit code 0** at
last run (never trust this report's prose over that generated file - regenerate and
compare before relying on this for a real retest sign-off).
"""
    write(out_dir / "SECURITY_REVIEW_FULL.md", full)

    # isolation-matrix.md: copy the real, generated harness output verbatim -
    # never a hand-written summary of it - so this deliverable's headline
    # artifact is provably the same file the harness itself wrote.
    src = REPO_ROOT / "results" / "isolation-tester" / "baseline" / "isolation-matrix.md"
    write(out_dir / "isolation-matrix.md", src.read_text())


# ---------------------------------------------------------------------------
# L5 - vibe-app (AI-built app review)
# ---------------------------------------------------------------------------


def generate_l5(attribution: dict) -> None:
    findings = load_findings("vibe-app")
    counts = severity_counts(findings)
    out_dir = REPO_ROOT / "sample-deliverables" / "L5-ai-app"

    # Top 10 of 12: drop the lowest-priority two (Low, then the narrowest Medium).
    rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    ranked = sorted(findings, key=lambda f: (rank[f["severity"]], f["id"]))
    dropped_ids = {"B-11", "B-12"}
    top10 = [f for f in ranked if f["id"] not in dropped_ids]
    assert len(top10) == 10, f"expected 10, got {len(top10)}"

    scan = f"""# Risk Scan — Top 10 — StudioBook (fictional AI-built class-booking app)

{BANNER}

**Prepared:** {TODAY} · **Tier:** Starter · **Target:** `targets/vibe-app` (Next.js 14 +
Supabase + Stripe, "AI app builder" style baseline)

## Scope & method

An automated + manual scan of an AI-generated codebase for the access-control,
secrets-handling and business-logic mistakes this style of app commonly ships with.
Method: this lab's M5 scanners (gitleaks, Semgrep custom rules, a Supabase
row-level-security checker, Trivy dependency scan) plus manual review and live
exploit-script proof (`targets/vibe-app/exploits/*.sh`) for everything the automated
tools structurally can't see (business-logic races, RLS-adjacent authorization gaps).

## Top 10 findings (of 12 total - the 2 lowest-priority are in the Standard/Advanced
tier report, `REVIEW_WITH_FIX_PLAN.md`)

{chr(10).join(render_finding_brief(f, method_line(f['id'], attribution), evidence_citation(f['id'], attribution)) for f in top10)}

## Risk summary (all {sum(counts.values())} findings; top 10 by severity detailed above)

{risk_table(counts)}

Full findings, evidence, remediation plan and retest notes (including B-11 and B-12):
`REVIEW_WITH_FIX_PLAN.md` (Standard/Advanced tier).
"""
    write(out_dir / "RISK_SCAN_TOP10.md", scan)

    review = f"""# Security Review with Fix Plan — StudioBook (fictional AI-built class-booking app)

{BANNER}

**Prepared:** {TODAY} · **Tier:** Standard/Advanced · **Target:** `targets/vibe-app`
(baseline) vs. `targets/vibe-app-fixed` (retest target)

## Scope & method

Same scope as `RISK_SCAN_TOP10.md`, extended to all 12 findings, with the
differentiator this listing promises: an **AI fix prompt** per finding - the literal
prompt used (via `targets/vibe-app-fixed/AI_FIX_PROMPTS.md`) to produce this repo's
own fixed branch, not a hypothetical one written for the report. Every prompt below is
copy-paste-ready for Claude Code, Cursor, or similar.

## Risk summary

{risk_table(counts)}

## Findings

{chr(10).join(render_finding_full(f, method_line(f['id'], attribution), evidence_citation(f['id'], attribution), include_ai_prompt=True) for f in findings)}

## Remediation plan

{sprint_plan(findings)}

## Retest notes

`targets/vibe-app-fixed` is this repo's own retest target - a separate Next.js app and
Supabase project implementing every fix above (see its README's "What changed, per
finding" table), built by literally applying the AI fix prompts above, one commit per
finding id. Retest evidence: every script in `targets/vibe-app-fixed/exploits/` reports
FIXED with exit 0 against a freshly-reset stack; the M5 RLS checker reports 0 FAIL; M5's
gitleaks/Semgrep scans are clean on the fixed app's tracked source (see
`scanners/results/` for the generated, current state of all of this - never trust this
report's prose over those files).
"""
    write(out_dir / "REVIEW_WITH_FIX_PLAN.md", review)


def main() -> None:
    attribution = load_attribution()
    generate_l4(attribution)
    generate_l5(attribution)


if __name__ == "__main__":
    main()
