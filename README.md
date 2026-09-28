# saas-security-review-lab

[![CI](https://github.com/muralikalluri/saas-security-review-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/muralikalluri/saas-security-review-lab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

Two deliberately vulnerable SaaS apps, a tenant-isolation testing harness that finds
cross-tenant leaks automatically, a Supabase RLS checker plus a small scanner suite, and
sample security reports where every finding has evidence, impact, fix, effort, and (for
the AI-app-review listing) a ready-to-paste AI fix prompt - the exact prompt actually
used to produce this repo's own fixed branch, not a hypothetical one.

This is the working proof behind two Upwork listings: **L4** (multi-tenant SaaS security
review with tenant isolation testing) and **L5** (security & code review of an AI-built
app with a fix plan).

## Demo

_Screen recording not yet captured - `npm run dev` / `docker compose up` walkthroughs are
below in Quickstart; a short demo GIF is on the list before this goes live on Upwork._

## Results

Every number below is checked against a committed, generated results file (see the
Source column to reproduce it yourself) - this table itself is prose, so re-verify
before trusting it over the file it cites.

| Metric | Result | Source |
|---|---|---|
| Target A findings with a fix commit in `tenant-api-fixed` | 13 / 13 | `sample-deliverables/L4-multitenant/SECURITY_REVIEW_FULL.md`'s per-finding `Diff:` line (all 13 point to the same commit - M3 fixed Target A in one commit, not one-per-finding) |
| Isolation-tester non-control probes vs. baseline | 185 probes, 7 findings (A-01..A-07) confirmed LEAK | `results/isolation-tester/baseline/isolation-matrix.md` |
| Isolation-tester non-control probes vs. fixed mode | 124 probes, **0 leaks**, exit 0 | `results/isolation-tester/fixed/isolation-matrix.md` |
| Target B findings with a fix commit in `vibe-app-fixed` | 12 / 12 | `sample-deliverables/L5-ai-app/REVIEW_WITH_FIX_PLAN.md`'s per-finding `Diff:` line - a real `git log` lookup per finding id, not asserted |
| Supabase RLS checker vs. fixed mode | 0 FAIL | `scanners/results/rls-checker/vibe-app-fixed/rls-matrix.md` |
| gitleaks vs. `vibe-app-fixed`'s tracked source | 0 hits | `scanners/results/gitleaks/vibe-app-fixed-tree.md` |
| Semgrep vs. `vibe-app-fixed`'s tracked source | 0 findings | `scanners/results/semgrep/vibe-app-fixed.json` |
| Findings by discovery method (25 total, A+B) | 7 harness · 6 tool · 12 manual | `scanners/results/attribution.md` |
| Dependency scan | 3 manifests scanned (Trivy) | `scanners/results/dependency-scan/*.json` |

`targets/vibe-app-fixed/exploits/B-*.sh` (12 scripts) were run by hand against a
freshly-reset stack during development and every one printed `FIXED`/exit 0. Target A has
no equivalent `tenant-api-fixed/exploits/` folder - its retest evidence is the
isolation-tester run against the fixed stack (`124 probes, 0 leaks` above), not exploit
scripts. `targets/tenant-api/exploits/A-*.sh` (13 scripts) only run against the vulnerable
baseline. None of this is captured to a committed results file the way the rows above are,
so re-run the B-series scripts yourself (`for f in targets/vibe-app-fixed/exploits/B-*.sh;
do ./"$f"; done`) rather than trusting this sentence alone.

## Architecture

```mermaid
flowchart TB
    subgraph L4["L4 listing — multi-tenant SaaS review"]
        A["Target A: tenant-api (LedgerLite)<br/>Java 21 / Spring Boot / Postgres / Keycloak<br/>13 seeded findings A-01..A-13"]
        AF["tenant-api-fixed<br/>same findings, all closed"]
        IT["isolation-tester<br/>replays every endpoint as a<br/>foreign tenant / lower role / spoofed header"]
        A -->|"probed by"| IT
        AF -->|"re-probed, 0 leaks"| IT
    end
    subgraph L5["L5 listing — AI-built app review"]
        B["Target B: vibe-app (StudioBook)<br/>Next.js 14 / Supabase / Stripe<br/>12 seeded findings B-01..B-12"]
        BF["vibe-app-fixed<br/>same findings, all closed,<br/>via AI_FIX_PROMPTS.md"]
        SC["scanners/<br/>gitleaks · Semgrep · RLS checker · Trivy"]
        B -->|"scanned by"| SC
        BF -->|"re-scanned, clean"| SC
    end
    IT --> ATTR["attribution.json<br/>tool vs harness vs manual"]
    SC --> ATTR
    ATTR --> RPT["report-templates/generate_reports.py"]
    RPT --> L4RPT["sample-deliverables/L4-multitenant/*"]
    RPT --> L5RPT["sample-deliverables/L5-ai-app/*"]
```

## Quickstart

**Target A (tenant-api, baseline vs. fixed):**

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8183/actuator/health          # baseline
curl http://localhost:8184/actuator/health           # fixed
cd targets/tenant-api/exploits && ./A-01-bola-invoice-by-id.sh   # reproduces the leak
```

**Target B (vibe-app, baseline) - run in one terminal:**

```bash
# .env is already committed here (that IS finding B-02) - no copy step needed
cd targets/vibe-app
supabase start && npm install && npm run dev
```

Then, in a second terminal, with the dev server above still running:

```bash
cd targets/vibe-app/exploits
./B-01-service-role-key-in-client-bundle.sh   # reproduces the leak
```

**Target B (vibe-app-fixed) - a separate terminal, separate Supabase project:**

```bash
cd targets/vibe-app-fixed
cp .env.example .env   # fill in ANON_KEY/SERVICE_ROLE_KEY from `supabase start`'s own output
supabase start && npm install && npm run dev
```

**Isolation-tester** (its own `.venv` first: `cd isolation-tester && python3 -m venv .venv
&& .venv/bin/pip install -r requirements.txt`, then from inside `isolation-tester/`):

```bash
.venv/bin/python -m isolation_tester run \
  --config config/tenant-api.baseline.yaml --openapi openapi/tenant-api.isolation.yaml \
  --run-name baseline --expect expectations/tenant-api.baseline.yaml
```

**Scanners** (from the repo root - a separate command, needs PyYAML, gitleaks and semgrep on PATH):

```bash
python3 scanners/verify_expected.py    # gitleaks + Semgrep + attribution, no live stack needed
```

See each target's own README for full setup, and `docs/method.md` for the review
methodology behind the sample deliverables.

## Features

- **Two realistic, deliberately-vulnerable targets** - a Java/Spring multi-tenant B2B API
  and a Next.js/Supabase/Stripe "AI app builder"-style app - each with a genuinely
  separate **fixed** counterpart (own database/project, never the same process as the
  baseline), so before/after is a real diff, not a toggle.
- **A reusable tenant-isolation test harness** (`isolation-tester/`) - not a fuzzer,
  a targeted replay of every endpoint as the wrong tenant/role/header, with
  request/response evidence saved per probe and a CI-usable exit code.
- **A purpose-built Supabase RLS checker** (`scanners/rls-checker/`) that reads the live
  Postgres catalog (not a regex over migration SQL) to correctly classify row-level
  security posture - including the Postgres semantics a naive checker gets wrong
  (`WITH CHECK` falling back to `USING`, per-role restrictive-policy scoping, the
  underlying-GRANT requirement).
- **A small scanner suite** (gitleaks with 3 custom rules, 2 custom Semgrep rules, Trivy)
  with a generated tool-vs-manual attribution report - not a marketing claim about method,
  an actual computed breakdown.
- **12 AI fix prompts, actually used** - `targets/vibe-app-fixed/AI_FIX_PROMPTS.md` was
  written before any fix, then applied one commit per finding; the sample deliverable's
  "AI fix prompt" field is that same prompt, not a fresh one written for the report.
- **Generated, not hand-typed, sample deliverables** - `report-templates/generate_reports.py`
  computes every count (severity totals, probe counts, tool-attribution) from the actual
  results files; PDF export via Pandoc + Tectonic.

## Design decisions

- **Fixed mode is a separate app/database/project, never a runtime toggle.** A shared
  codebase with an `if (fixed)` branch would mean the "vulnerable" path silently rots as
  soon as anyone edits the "fixed" one. Two independent apps means the baseline is
  guaranteed byte-for-byte stable, and the fixed one can be reviewed as a real diff.
- **The isolation-tester classifies by replaying, not by asserting.** Every probe records
  an actual request/response pair as evidence rather than a pass/fail assertion alone -
  the point of the tool is to be independently checkable, not just self-reported.
- **The RLS checker reads the live catalog, not the migration files.** Migrations are
  applied in order and can be superseded; only the replayed, final catalog state
  (`pg_class`, `pg_policies`, `has_table_privilege`) is trustworthy. This caught a real
  bug during development: Supabase's default ACLs grant broad table/function privileges
  to `authenticated` on every new object, which a checker trusting the migration source
  alone would miss entirely.
- **Attribution is computed from each tool's own declared output, not proximity.** An
  early version of the attribution script credited a finding if any tool hit landed
  within N lines of that finding's comment - too coarse, since a heuristic Semgrep rule
  legitimately also fires on unrelated, similarly-shaped code nearby. The final version
  only credits a finding when the specific tool/rule declares that exact target
  (`metadata.finding`, a gitleaks rule's `tags`, or the RLS checker's own verdict fields).
- **Every generated number cites its source file.** Report counts, matrix results, and
  this README's own Results table are all reproducible by re-running the script or tool
  that produced them - never asserted from memory.

## Sample deliverable

[`sample-deliverables/L5-ai-app/REVIEW_WITH_FIX_PLAN.md`](sample-deliverables/L5-ai-app/REVIEW_WITH_FIX_PLAN.md)
([PDF](sample-deliverables/L5-ai-app/REVIEW_WITH_FIX_PLAN.pdf)) - the full 12-finding
report for Target B, including the actual AI fix prompt used for each finding and a
sprint-grouped remediation plan. See `sample-deliverables/` for all 4 deliverables
(2 per listing, Starter and Standard/Advanced tiers).

## Documentation

- [`SPEC.md`](SPEC.md) — full specification, seeded findings, milestone plan
- [`docs/method.md`](docs/method.md) — review methodology (manual + automated)
- [`report-templates/README.md`](report-templates/README.md) — how the sample deliverables are generated
- Each target/tool directory has its own README with setup and verification steps

## MVP status

Milestones M0–M7 (`SPEC.md` §7) are complete. M8 ("CI job running isolation tester
against fixed mode on every push") is explicitly out of MVP scope ("Later") and not
implemented.

## Hire me

This repo is the working proof behind my Upwork listings for multi-tenant SaaS security
reviews and AI-built app security reviews with a fix plan - **[find me on Upwork](https://www.upwork.com/)**
(profile link to be added) or open an issue here with questions about the approach.
