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
- `results/isolation-tester/baseline/isolation-matrix.json` (M2) - Target
  A's harness proof; the generator counts LEAK/DENIED/control probes from
  this file itself, and `isolation-matrix.md` is copied into the L4
  deliverable verbatim (never re-summarised by hand).

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
pandoc SECURITY_REVIEW_FULL.md -o SECURITY_REVIEW_FULL.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc

cd ../L5-ai-app
pandoc REVIEW_WITH_FIX_PLAN.md -o REVIEW_WITH_FIX_PLAN.pdf \
  --pdf-engine=tectonic -V geometry:margin=1in -V colorlinks=true --toc
```

`tectonic` (a small, self-contained LaTeX engine - `brew install tectonic`) is
pandoc's PDF engine here instead of a full TeX distribution, which would be
several GB. Both PDFs are committed alongside their source `.md` for the
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
