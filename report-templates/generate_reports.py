#!/usr/bin/env python3
"""Deliberately insecure for demonstration. Do not deploy.

Generates the 4 sample deliverables (SPEC.md section 1/5/7) from:
  - report-templates/findings-data/{tenant-api,vibe-app}.yml (per-finding
    detail - severity, OWASP mapping, analyst prose)
  - scanners/results/attribution.json (tool/harness/manual, M5's own output)
  - results/isolation-tester/{baseline,fixed}/isolation-matrix.json (Target
    A's harness proof, both runs - counts computed here, never hand-typed)
  - targets/vibe-app-fixed/AI_FIX_PROMPTS.md (parsed directly - the AI fix
    prompt shown per L5 finding is a genuine excerpt of that file, not a
    second, hand-copied version that can drift from it)
  - `git log` (which commit actually fixed each finding)

Per the repo's global CLAUDE.md ("never hand-type performance numbers...
generate them from results files"): every COUNT in the generated reports
(severity totals, probe totals, tool-attribution totals) is computed from
these files by this script. The per-finding narrative (what/impact/fix) is
analyst prose living in the findings-data YAML, same as a real pentester's
write-up - that's the deliverable's actual content, not a "score".

Run: python3 report-templates/generate_reports.py
Output: sample-deliverables/L4-multitenant/*.md, sample-deliverables/L5-ai-app/*.md
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "report-templates"
# The "Prepared" date is generation time, like any report's letterhead date -
# it's EXPECTED to differ across runs on different days; that's not a
# reproducibility bug (everything else this script emits is byte-stable for
# the same source files, which is what "generated, not hand-typed" is
# actually about).
TODAY = date.today().isoformat()

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
BANNER = "> Deliberately insecure for demonstration and training. Do not deploy. Run locally only."
# Same anchor CLAUDE.md requires at every flaw's own comment (and that
# scanners/attribution/build_attribution.py already keys on) - reused here
# to turn attribution.json's file-level evidence_files into a real file:line
# citation, instead of hand-typing a line number into the findings-data YAML.
SEEDED_FLAW_RE = re.compile(r"\b([AB]-\d\d)\s*\(seeded flaw")


def target_root_for(finding_id: str) -> str:
    return "targets/tenant-api/" if finding_id.startswith("A-") else "targets/vibe-app/"


def evidence_locations(finding_id: str, attribution: dict) -> list[str]:
    """[[relative-to-target-root path]:line, ...] - relative to the target's
    own root (not the full repo path) to shorten these, PLUS a zero-width
    space after every remaining "/" so tectonic/LaTeX can still wrap a long
    one (Java's package-per-directory paths, e.g. tenant-api's
    `src/main/java/com/ledgerlite/tenantapi/invoice/InvoiceController.java`,
    are long enough on their own to overflow the page margin by 200pt+ even
    after shortening - measured directly: shortening the path ALONE was not
    sufficient, a milestone review caught real overflow in the rendered PDF
    even after an earlier version of this function shortened paths without
    also keeping the zero-width-space break points)."""
    root = target_root_for(finding_id)
    all_files = attribution.get(finding_id, {}).get("evidence_files", [])
    # attribution.json's evidence scan runs over all of targets/ - once
    # targets/vibe-app-fixed/ existed as a copy that (deliberately) still
    # carries the SAME "ID (seeded flaw" comment in its own untouched copy
    # of the original migrations (documenting what WAS wrong, even after a
    # later migration fixes it), that scan started returning both the
    # baseline's evidence file AND the fixed module's copy of it. This
    # report is about the baseline - keep only evidence under the
    # baseline's own root.
    files = [f for f in all_files if f.startswith(root)]
    out = []
    for rel_path in files:
        path = REPO_ROOT / rel_path
        line_no = None
        try:
            for i, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
                m = SEEDED_FLAW_RE.search(line)
                if m and m.group(1) == finding_id:
                    line_no = i
                    break
        except OSError:
            pass
        short = rel_path.removeprefix(root)
        out.append(f"{short}:{line_no}" if line_no else short)
    if not out:
        return ["see targets/*/exploits/ for reproduction steps"]
    return [loc.replace("/", "/​") for loc in out]


def fix_commits(finding_id: str, target_dir: str) -> list[str]:
    """Short hashes of every commit whose subject names this finding, under
    target_dir, oldest first - i.e. the actual `git diff`(s) a reader can pull
    up as the "exact fix (code diff)" SPEC.md §4 asks for, instead of
    embedding a (potentially huge, 25-finding) diff inline in the report.
    Some findings needed a follow-up commit after the first one turned out to
    be incomplete (see AI_FIX_PROMPTS.md's "Deviations" section for B-08) -
    citing only the first match would point a reader at a diff that isn't the
    whole fix, so this returns every match rather than the first one."""
    proc = subprocess.run(
        ["git", "log", "--oneline", "--reverse", "--", target_dir],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    hashes = []
    for line in proc.stdout.splitlines():
        short_hash, _, subject = line.partition(" ")
        if re.search(rf"\b{re.escape(finding_id)}\b", subject):
            hashes.append(short_hash)
    return hashes


def load_findings(target: str) -> list[dict]:
    data = yaml.safe_load((TEMPLATES / "findings-data" / f"{target}.yml").read_text())
    return data["findings"]


def load_attribution() -> dict:
    return json.loads((REPO_ROOT / "scanners" / "results" / "attribution.json").read_text())


def load_isolation_matrix(run: str) -> dict:
    return json.loads((REPO_ROOT / "results" / "isolation-tester" / run / "isolation-matrix.json").read_text())


def parse_ai_fix_prompts() -> dict[str, str]:
    """{finding_id: prompt body} parsed directly from
    targets/vibe-app-fixed/AI_FIX_PROMPTS.md - genuinely the same text, not
    a second hand-copied version that can drift from it (a milestone review
    caught exactly that drift in an earlier version of this script, down to
    a prompt naming a function from the FIXED code instead of the one that
    existed in the baseline when the prompt was supposedly written)."""
    text = (REPO_ROOT / "targets" / "vibe-app-fixed" / "AI_FIX_PROMPTS.md").read_text()
    sections = re.split(r"^## (B-\d\d) — .*$", text, flags=re.MULTILINE)
    # re.split with a capturing group yields [prefix, id, body, id, body, ...]
    prompts = {}
    for i in range(1, len(sections), 2):
        finding_id = sections[i]
        body = sections[i + 1].split("\n## ", 1)[0].strip()
        prompts[finding_id] = body
    return prompts


def parse_deviations() -> dict[str, str]:
    """{finding_id: deviation note} parsed from AI_FIX_PROMPTS.md's own
    "Deviations during implementation" section, so the report surfaces every
    place a milestone review found the pre-implementation prompt doesn't
    accurately describe what actually got built or shipped an incomplete fix
    - right next to the prompt text itself, not just in the source file."""
    text = (REPO_ROOT / "targets" / "vibe-app-fixed" / "AI_FIX_PROMPTS.md").read_text()
    marker = "## Deviations during implementation"
    idx = text.find(marker)
    if idx == -1:
        return {}
    section = text[idx + len(marker):].strip()
    bullets = re.split(r"\n(?=- \*\*B-\d\d)", section)
    deviations: dict[str, str] = {}
    for bullet in bullets:
        m = re.match(r"- \*\*(B-\d\d)", bullet)
        if m:
            body = re.sub(r"^- ", "", bullet.strip())
            body = re.sub(r"\s*\n\s*", " ", body)  # unwrap the source's line-wrapping
            deviations[m.group(1)] = body
    return deviations


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


def render_evidence_bullets(locations: list[str]) -> str:
    return "\n".join(f"- `{loc}`" for loc in locations)


def render_finding_full(f: dict, method: str, locations: list[str], commits: list[str], ai_prompt: str | None, deviation: str | None = None) -> str:
    lines = [
        f"### {f['id']} — {f['severity']}",
        "",
        f"**OWASP:** {f['owasp_2021']} · {f['owasp_api_2023']}  ",
        f"**Effort to fix:** {f['effort']}  ",
        f"**How found:** {method}",
        "",
        "**Evidence:**",
        "",
        render_evidence_bullets(locations),
        "",
        f"**What's wrong.** {f['what']}",
        "",
        f"**Why it matters.** {f['impact']}",
        "",
        f"**Exact fix.** {f['fix']}",
    ]
    if commits:
        diffs = ", ".join(f"`git show {c}`" for c in commits)
        note = "" if len(commits) == 1 else " (a follow-up commit after the first fix was found incomplete)"
        lines.append(f"  Diff: {diffs}{note}.")
    if ai_prompt:
        lines += ["", "**AI fix prompt** (copy-paste into Claude Code / Cursor):", "", "```text", ai_prompt, "```"]
    if deviation:
        lines += ["", f"> **Deviation from the prompt above, caught in review:** {deviation}"]
    lines.append("")
    return "\n".join(lines)


def render_finding_brief(f: dict, method: str, locations: list[str]) -> str:
    return (
        f"### {f['id']} — {f['severity']}\n\n"
        f"**OWASP:** {f['owasp_2021']} · {f['owasp_api_2023']} · **How found:** {method}\n\n"
        f"**Evidence:**\n\n{render_evidence_bullets(locations)}\n\n"
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
    baseline_iso = isolation_summary(load_isolation_matrix("baseline"))
    fixed_iso = isolation_summary(load_isolation_matrix("fixed"))
    out_dir = REPO_ROOT / "sample-deliverables" / "L4-multitenant"
    a_commits = fix_commits("A-01", "targets/tenant-api-fixed")
    fixed_commit = a_commits[0] if a_commits else "see targets/tenant-api-fixed/README.md"

    top = [f for f in findings if f["severity"] in ("Critical", "High")]
    top_heading = f"## Top findings (Starter tier - {len(top)} of {len(findings)} total; see the Standard/Advanced tier report for the complete finding set)"

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

{top_heading}

{chr(10).join(render_finding_brief(f, method_line(f['id'], attribution), evidence_locations(f['id'], attribution)) for f in top)}

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
see `isolation-matrix.md` (this directory) for the full endpoint×actor matrix. Every LEAK
row's own request/response capture is committed under
`results/isolation-tester/baseline/raw/` (the path is in that row's Evidence column) -
DENIED/control-row captures are regenerated locally on each harness run rather than
committed, to keep this repo small.

**Harness run summary, baseline** (from `results/isolation-tester/baseline/isolation-matrix.json`):
{baseline_iso['non_control_probes']} non-control probes across every declared endpoint × actor
combination ({baseline_iso['control_probes']} additional positive-control probes confirmed
legitimate owner access still works), preflight {'OK' if baseline_iso['preflight_ok'] else 'FAILED'},
positive controls {'OK' if baseline_iso['controls_ok'] else 'FAILED'}. **{baseline_iso['leak_count']} probes
classified LEAK**, confirming findings {', '.join(baseline_iso['confirmed_findings'])} mechanically. This run's
own exit code is {baseline_iso['exit_code']} - against this baseline profile the harness exits 0 when it finds
*exactly* the expected/already-known leaks (its job here is regression detection against a target that's
supposed to stay vulnerable), not when it finds none; see the fixed-mode run below for the "0 leaks" result.

**Harness run summary, fixed** (from `results/isolation-tester/fixed/isolation-matrix.json`):
{fixed_iso['non_control_probes']} non-control probes ({fixed_iso['control_probes']} positive controls),
**{fixed_iso['leak_count']} probes classified LEAK**, exit code **{fixed_iso['exit_code']}**.

## Risk summary

{risk_table(counts)}

## Findings

{chr(10).join(render_finding_full(f, method_line(f['id'], attribution), evidence_locations(f['id'], attribution), a_commits, None) for f in findings)}

## Remediation plan

{sprint_plan(findings)}

## Retest notes

`targets/tenant-api-fixed` is this repo's own retest target: a separate Maven
module/database/Keycloak realm implementing every fix above in commit `{fixed_commit}`
(`git show {fixed_commit}`; see also its own README's "What changed, per finding" table).
Re-running the SAME isolation-tester config against it is the retest evidence - see the
"Harness run summary, fixed" line above, computed from
`results/isolation-tester/fixed/isolation-matrix.json` (never trust this report's prose
over that generated file - regenerate and compare before relying on this for a real
retest sign-off).
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
    ai_prompts = parse_ai_fix_prompts()
    deviations = parse_deviations()
    out_dir = REPO_ROOT / "sample-deliverables" / "L5-ai-app"

    gitleaks_tree = json.loads((REPO_ROOT / "scanners" / "results" / "gitleaks" / "vibe-app-fixed-tree.json").read_text())
    tracked = set(
        subprocess.run(["git", "ls-files", "targets/vibe-app-fixed"], cwd=REPO_ROOT, capture_output=True, text=True)
        .stdout.splitlines()
    )
    gitleaks_tracked_hits = len([f for f in gitleaks_tree if f["File"] in tracked])
    rls_matrix_fixed = json.loads((REPO_ROOT / "scanners" / "results" / "rls-checker" / "vibe-app-fixed" / "rls-matrix.json").read_text())
    rls_fail_count = len([r for r in rls_matrix_fixed if r["verdict"] == "FAIL"])
    semgrep_fixed = json.loads((REPO_ROOT / "scanners" / "results" / "semgrep" / "vibe-app-fixed.json").read_text())
    semgrep_fixed_hits = len(semgrep_fixed.get("results", []))

    # Top N by severity, dropping the lowest-priority findings for the
    # Starter tier - the drop is by rank, computed here, not a hand-picked ID
    # set (so it stays correct if findings-data/vibe-app.yml's severities
    # ever change).
    STARTER_DROP = 2
    rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    ranked = sorted(findings, key=lambda f: (rank[f["severity"]], f["id"]))
    top_n = ranked[:-STARTER_DROP] if STARTER_DROP else ranked

    top_heading = f"## Top {len(top_n)} findings (of {len(findings)} total - the {STARTER_DROP} lowest-priority are in the Standard/Advanced tier report, `REVIEW_WITH_FIX_PLAN.md`)"

    scan = f"""# Risk Scan — Top {len(top_n)} — StudioBook (fictional AI-built class-booking app)

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

{top_heading}

{chr(10).join(render_finding_brief(f, method_line(f['id'], attribution), evidence_locations(f['id'], attribution)) for f in top_n)}

## Risk summary (all {sum(counts.values())} findings; top {len(top_n)} by severity detailed above)

{risk_table(counts)}

Full findings, evidence, remediation plan and retest notes: `REVIEW_WITH_FIX_PLAN.md`
(Standard/Advanced tier).
"""
    write(out_dir / "RISK_SCAN_TOP10.md", scan)

    review = f"""# Security Review with Fix Plan — StudioBook (fictional AI-built class-booking app)

{BANNER}

**Prepared:** {TODAY} · **Tier:** Standard/Advanced · **Target:** `targets/vibe-app`
(baseline) vs. `targets/vibe-app-fixed` (retest target)

## Scope & method

Same scope as `RISK_SCAN_TOP10.md`, extended to all {len(findings)} findings, with the
differentiator this listing promises: an **AI fix prompt** per finding, parsed directly
from `targets/vibe-app-fixed/AI_FIX_PROMPTS.md` (the file written before any fix, then
actually used to build this repo's own fixed branch) - not re-typed into this report,
so it can't silently drift from what was really run. B-11 has no separate prompt (its
fix landed inside the B-04 commit - see that entry below); its excerpt says so rather
than inventing one.

## Risk summary

{risk_table(counts)}

## Findings

{chr(10).join(render_finding_full(f, method_line(f['id'], attribution), evidence_locations(f['id'], attribution), fix_commits(f['id'], "targets/vibe-app-fixed"), ai_prompts.get(f['id']), deviations.get(f['id'])) for f in findings)}

## Remediation plan

{sprint_plan(findings)}

## Retest notes

`targets/vibe-app-fixed` is this repo's own retest target - a separate Next.js app and
Supabase project implementing every fix above (see its README's "What changed, per
finding" table and the per-finding commit references above), built by applying the AI
fix prompts above, one commit per finding id (B-03/B-04/B-11 share one commit - see the
B-11 entry above for why). Retest evidence, all from committed, generated results files:

- RLS checker vs. the fixed stack: `scanners/results/rls-checker/vibe-app-fixed/rls-matrix.md` - {rls_fail_count} FAIL.
- gitleaks vs. the fixed module's current tree: `scanners/results/gitleaks/vibe-app-fixed-tree.md` -
  **{gitleaks_tracked_hits} hits in git-tracked files** (any hits are in the local, gitignored `.env` only).
- Semgrep vs. the fixed module's current tree: `scanners/results/semgrep/vibe-app-fixed.json` -
  **{semgrep_fixed_hits} findings** (the B-01/B-05 patterns this ruleset targets are both gone).
- Every script in `targets/vibe-app-fixed/exploits/` was run by hand against a freshly-reset
  stack during development and printed `FIXED` with exit 0 - not yet captured to a
  committed results file (unlike the three checks above); re-run them yourself to confirm
  before relying on this line for a real retest sign-off.
"""
    write(out_dir / "REVIEW_WITH_FIX_PLAN.md", review)


def main() -> None:
    attribution = load_attribution()
    generate_l4(attribution)
    generate_l5(attribution)


if __name__ == "__main__":
    main()
