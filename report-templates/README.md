# report-templates

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

M7 (`SPEC.md` §5/§7). One shared report structure - cover, scope & method, a
summary risk table, per-finding detail (what's wrong / why it matters /
evidence / exact fix / effort / OWASP mapping, plus an AI fix prompt for the
L5 listing specifically), a remediation plan grouped into sprints, and
retest notes - rendered into the 4 sample deliverables named in `SPEC.md`
§1's table.

## Nothing here is hand-typed

Per the repo's global CLAUDE.md ("never hand-type performance numbers...
generate them from results files"), every **count** in a generated report
(severity totals, the isolation-tester's probe/leak counts, tool-found vs
manual totals) is computed by `generate_reports.py` from the actual results
files - never asserted in the report body by hand:

- `findings-data/{tenant-api,vibe-app}.yml` - per-finding severity, OWASP
  mapping, and analyst prose (what/impact/fix/effort). This IS the
  deliverable's actual content, same as a real pentester's findings write-up
  - not a "score" the CLAUDE.md rule is about. Severity assignment is
    genuine analyst judgement; everything downstream of it (the risk
    table's counts, the sprint grouping) is computed FROM this file, never
    separately hand-typed into the rendered report.
- `scanners/results/attribution.json` (M5) - which findings were tool-found,
  harness-found, or manual, read directly for each finding's "How found"
  line.
- `results/isolation-tester/{baseline,fixed}/isolation-matrix.json` (M2) -
  Target A's harness proof, both before and after the fix; the generator
  counts LEAK/DENIED/control probes from these files itself, and
  `isolation-matrix.md` (baseline) is copied into the L4 deliverable
  verbatim (never re-summarised by hand).
- `scanners/results/rls-checker/vibe-app-fixed/rls-matrix.json` (M5/M6) -
  the fixed-mode RLS retest line's FAIL count.
- `scanners/results/gitleaks/vibe-app-fixed-tree.json` and
  `scanners/results/semgrep/vibe-app-fixed.json` (M6) - the fixed-mode
  gitleaks/semgrep retest counts, cross-referenced against `git ls-files`
  to separate tracked hits from the local, gitignored `.env`.
- `targets/vibe-app-fixed/AI_FIX_PROMPTS.md` - the L5 report's AI fix
  prompts and "Deviation from the prompt" notes are parsed directly from
  this file at generation time, not a second hand-copied version that
  could drift from it (see the file's own header for why).
- `git log` - each finding's "Diff:" citation is a real commit hash found
  by searching commit subjects for the finding id, not a placeholder.

## Generate (or regenerate) the reports

```bash
cd report-templates
python3 -m venv .venv && .venv/bin/pip install PyYAML
.venv/bin/python generate_reports.py
```

Writes:

- `sample-deliverables/L4-multitenant/ARCHITECTURE_REVIEW.md` (Starter)
- `sample-deliverables/L4-multitenant/SECURITY_REVIEW_FULL.md` (Standard/Advanced)
- `sample-deliverables/L4-multitenant/isolation-matrix.md` (copied verbatim from `results/`)
- `sample-deliverables/L5-ai-app/RISK_SCAN_TOP10.md` (Starter)
- `sample-deliverables/L5-ai-app/REVIEW_WITH_FIX_PLAN.md` (Standard/Advanced)

Re-run this script any time a finding's severity/fix text changes, or the
underlying results files are regenerated (a new isolation-tester run, a new
attribution.json) - never hand-edit the generated `.md` files directly.

## PDF export

```bash
cd sample-deliverables/L4-multitenant
pandoc ARCHITECTURE_REVIEW.md -o ARCHITECTURE_REVIEW.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc
pandoc SECURITY_REVIEW_FULL.md -o SECURITY_REVIEW_FULL.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc

cd ../L5-ai-app
pandoc RISK_SCAN_TOP10.md -o RISK_SCAN_TOP10.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc
pandoc REVIEW_WITH_FIX_PLAN.md -o REVIEW_WITH_FIX_PLAN.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc
```

Evidence citations get a zero-width space (U+200B) inserted after every `/` -
pandoc turns this into a real `\hspace{0pt}` break point in the generated
LaTeX, letting `tectonic` wrap even a long, deeply-nested Java package path
instead of overflowing the page margin (this was a real, measured bug during
authoring - the very first version of this shortened evidence paths but
dropped the break-point insertion, and still overflowed by 200pt+; both are
needed together).

`tectonic` (a small, self-contained LaTeX engine - `brew install tectonic`) is
pandoc's PDF engine here instead of a full TeX distribution, which would be
several GB. All 4 PDFs are committed alongside their source `.md` for the
portfolio - regenerate them with the same command after any content change
rather than hand-editing the PDF.

## Which findings were tool-found vs manually found

Both L4 and L5 reports state this per finding (the "How found" line), sourced
from `scanners/results/attribution.json` - see `scanners/README.md`'s
Attribution section for exactly how that file itself is derived. Most of
Target A's findings are **harness**-found (the isolation-tester mechanically
reproduces them); most of Target B's are **manual** (business-logic/authz
gaps a scanner can't structurally see) with a handful **tool**-found (secrets,
RLS posture) - this split is itself part of the "not just an automated scan"
positioning `SPEC.md` §6 calls out.
