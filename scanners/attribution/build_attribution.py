#!/usr/bin/env python3
"""Deliberately insecure for demonstration. Do not deploy.

Builds scanners/results/attribution.json + attribution.md: which findings
were TOOL-found, HARNESS-found, or found only by MANUAL review/exploit
script (SPEC.md section 6: "The report states which findings were
tool-found vs manually found"). Per the repo's global CLAUDE.md ("never
hand-type numbers into docs - generate them from results files"), the
method for every finding is DERIVED from actual results files, never
asserted independently here:

  1. HARNESS: the id appears in results/isolation-tester/baseline's own
     `actual_leaks` list - the isolation-tester's real output.
  2. TOOL: not harness-found, AND a scanner's own output says, in its own
     terms, that it found this specific id:
       - Semgrep: each rule declares `metadata.finding: B-xx` in
         scanners/semgrep-rules/vibe-app.yml - read straight from that
         rule's real hits in scanners/results/semgrep/vibe-app.json.
         (An earlier version of this script tried "any tool hit within N
         lines of the id's comment" - too coarse: b05's rule fires on
         other, structurally-similar, ALSO-privileged code nearby (see the
         rule's own documented false-positive caveat), which is real and
         worth a human's attention, but isn't evidence for whatever OTHER
         finding's comment happens to sit in the same file. Reading the
         rule's own declared target avoids attributing a heuristic hit to
         the wrong finding.)
       - gitleaks custom rules: same idea via each rule's `tags` in
         scanners/gitleaks/gitleaks.toml (an `A-xx`/`B-xx` tag).
       - gitleaks's builtin `jwt` rule (not ours to tag) only ever fires on
         targets/vibe-app/.env, on one of two lines holding the SAME
         service-role JWT under two different variable names - resolved by
         reading that exact source line: a NEXT_PUBLIC_ prefix means B-01
         (shipped to the browser), otherwise B-02 (committed secret).
       - RLS checker: its own verdict rows already carry (schema, table,
         cmd) - mapped directly to B-03/B-04 (the only two RLS findings;
         `classes` is allowlisted and intentional, not a finding).
  3. MANUAL: neither of the above - proven only by the exploit script in
     targets/*/exploits/.

"evidence_files" (for the report table) is still every file where the id's
own "ID (seeded flaw" comment appears (CLAUDE.md's required convention) -
that part is unrelated to the method decision above, purely informational.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNERS = REPO_ROOT / "scanners"
# Anchored to the exact "ID (seeded flaw" convention CLAUDE.md requires at
# every flaw's OWN comment - deliberately narrower than "the id appears
# anywhere in this file", which would also catch legitimate cross-references
# in prose (e.g. "...which is where B-06 and B-10 actually live").
ID_RE = re.compile(r"\b([AB]-\d\d)\s*\(seeded flaw")
EVIDENCE_ROOTS = [REPO_ROOT / "targets", REPO_ROOT / "docker-compose.yml"]
EVIDENCE_SUFFIXES = {".ts", ".tsx", ".java", ".yml", ".yaml", ".sql", ".toml", ".properties"}
SKIP_DIR_NAMES = {
    "node_modules", ".venv", ".next", "target", "results", "__pycache__",
    ".pytest_cache", "exploits", ".git",
}

RLS_TABLE_TO_FINDING = {
    ("public", "bookings", None): "B-03",
    ("public", "profiles", "SELECT"): "B-04",
}


def find_evidence_files() -> dict[str, set[str]]:
    """Informational only (report column) - see module docstring."""
    evidence: dict[str, set[str]] = {}

    def scan_file(path: Path) -> None:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            return
        rel = str(path.relative_to(REPO_ROOT))
        for m in ID_RE.finditer(text):
            evidence.setdefault(m.group(1), set()).add(rel)

    for root in EVIDENCE_ROOTS:
        if root.is_file():
            scan_file(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            if path.suffix not in EVIDENCE_SUFFIXES and path.name != ".env":
                continue
            scan_file(path)
    return evidence


def load_harness_ids() -> set[str]:
    path = REPO_ROOT / "results" / "isolation-tester" / "baseline" / "isolation-matrix.json"
    data = json.loads(path.read_text())
    return set(data["actual_leaks"])


def load_gitleaks_rule_tags() -> dict[str, set[str]]:
    """{rule_id: {A-xx/B-xx tags}} straight from our own gitleaks.toml."""
    import tomllib

    data = tomllib.loads((SCANNERS / "gitleaks" / "gitleaks.toml").read_text())
    out = {}
    for rule in data.get("rules", []):
        tags = {t for t in rule.get("tags", []) if re.fullmatch(r"[AB]-\d\d", t)}
        if tags:
            out[rule["id"]] = tags
    return out


def resolve_tool_findings(evidence_files: dict[str, set[str]]) -> dict[str, set[str]]:
    """{tool_name: {finding_ids it actually found, per its OWN declared
    target}}.

    A rule can be tagged with more than one finding id when the same
    pattern legitimately serves both (e.g. "a secret-named key with a bare
    literal value" fires on both A-09's application.yml and B-02's .env) -
    each individual HIT is only credited to the tag(s) whose finding
    actually has evidence in that hit's file, not every tag the rule
    carries. A milestone review caught this as a real bug: without the
    file check, .env:28 (a B-02 secret) was wrongly credited to A-09 just
    because the same rule that catches A-09 also happens to catch it.
    """
    found: dict[str, set[str]] = {"rls-checker": set(), "semgrep": set(), "gitleaks": set()}

    rls_path = SCANNERS / "results" / "rls-checker" / "vibe-app" / "rls-matrix.json"
    if rls_path.exists():
        for f in json.loads(rls_path.read_text()):
            if f["verdict"] != "FAIL":
                continue
            key = (f["schema"], f["table"], f["cmd"])
            if key in RLS_TABLE_TO_FINDING:
                found["rls-checker"].add(RLS_TABLE_TO_FINDING[key])

    semgrep_path = SCANNERS / "results" / "semgrep" / "vibe-app.json"
    if semgrep_path.exists():
        data = json.loads(semgrep_path.read_text())
        for r in data.get("results", []):
            fid = r.get("extra", {}).get("metadata", {}).get("finding")
            if fid and r["path"] in evidence_files.get(fid, set()):
                found["semgrep"].add(fid)

    gitleaks_path = SCANNERS / "results" / "gitleaks" / "report.json"
    if gitleaks_path.exists():
        rule_tags = load_gitleaks_rule_tags()
        data = json.loads(gitleaks_path.read_text()) or []
        for hit in data:
            rule_id = hit["RuleID"]
            if rule_id in rule_tags:
                for tag in rule_tags[rule_id]:
                    if hit["File"] in evidence_files.get(tag, set()):
                        found["gitleaks"].add(tag)
            elif rule_id == "jwt" and hit["File"] == "targets/vibe-app/.env":
                lines = (REPO_ROOT / hit["File"]).read_text().splitlines()
                source_line = lines[hit["StartLine"] - 1]
                found["gitleaks"].add("B-01" if "NEXT_PUBLIC" in source_line else "B-02")

    return found


def main() -> None:
    findings = yaml.safe_load((Path(__file__).parent / "findings.yml").read_text())["findings"]
    evidence_files = find_evidence_files()
    harness_ids = load_harness_ids()
    tool_findings = resolve_tool_findings(evidence_files)

    attribution = {}
    for f in findings:
        fid = f["id"]
        if fid in harness_ids:
            method, tools = "harness", ["isolation-tester"]
        else:
            matching_tools = sorted(name for name, ids in tool_findings.items() if fid in ids)
            method, tools = ("tool", matching_tools) if matching_tools else ("manual", [])
        attribution[fid] = {
            "title": f["title"],
            "method": method,
            "tools": tools,
            "evidence_files": sorted(evidence_files.get(fid, [])),
        }

    out_json = SCANNERS / "results" / "attribution.json"
    out_json.write_text(json.dumps(attribution, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Tool-found vs manually-found findings",
        "",
        "> Deliberately insecure for demonstration. Do not deploy. Run locally only.",
        "",
        "Generated by `scanners/attribution/build_attribution.py` from actual scanner/harness "
        "output files - never hand-typed (CLAUDE.md). Re-run after any scanner or exploit change.",
        "",
        "| ID | Method | Tool(s) | Title |",
        "|---|---|---|---|",
    ]
    for fid in sorted(attribution, key=lambda k: (k[0], int(k[2:]))):
        a = attribution[fid]
        tools = ", ".join(a["tools"]) or "-"
        lines.append(f"| {fid} | {a['method']} | {tools} | {a['title']} |")
    counts: dict[str, int] = {}
    for a in attribution.values():
        counts[a["method"]] = counts.get(a["method"], 0) + 1
    lines += ["", "**Totals:** " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))]
    (SCANNERS / "results" / "attribution.md").write_text("\n".join(lines) + "\n")

    print(f"wrote {out_json}")
    print(f"wrote {SCANNERS / 'results' / 'attribution.md'}")
    print(counts)


if __name__ == "__main__":
    main()
