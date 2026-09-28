# Review methodology

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

How the findings in this repo's sample deliverables (`sample-deliverables/`)
were actually produced - not a generic "how a pentest works" essay, but the
specific manual/automated split used here, with pointers to the tool that
found each thing.

## The three ways a finding gets into a report

1. **Harness-found** (`isolation-tester/`, M2) - a reusable CLI that replays
   every declared endpoint as a foreign tenant, a lower role, a spoofed
   header, and a mass-assigned tenant id, then classifies each response as
   `LEAK` or `DENIED`. This is Target A's headline method: cross-tenant
   authorization bugs (BOLA/BOPLA/BFLA-shaped) are *mechanically reproduced*,
   not just spotted by eye. See `isolation-tester/README.md` for the exit-code
   policy and `results/isolation-tester/baseline/isolation-matrix.md` for the
   actual, current output (generated, never hand-edited).

2. **Tool-found** (`scanners/`, M5) - gitleaks (secrets, extended with two
   custom rules for shapes the defaults miss), Semgrep (two custom rules:
   a NEXT_PUBLIC service-role pattern, a missing-ownership-check heuristic),
   a purpose-built Supabase RLS checker (queries the live Postgres catalog
   for row-level-security posture - not a regex over migration SQL), and
   Trivy (dependency CVEs, informational only). See `scanners/README.md` for
   how each one works and its documented false-positive/negative limits.

3. **Manual** - read the code, understand the business logic, exploit it by
   hand (`targets/*/exploits/*.sh` are the reproducible proof of this, one
   curl-based script per finding). This is where business-logic bugs live
   that no scanner or harness can structurally see: a missing idempotency
   check on a webhook, a booking route that doesn't validate quantity, a
   server-side role check that's just... absent. Most of Target B's findings
   are this category - see the note below on why.

## Which method found which finding

Never hand-typed here or in the sample deliverables - `scanners/attribution/
build_attribution.py` derives it directly from each tool's own actual output
(the harness's `actual_leaks` list, Semgrep's `metadata.finding` per rule,
gitleaks' rule tags, the RLS checker's verdict rows) and writes
`scanners/results/attribution.json` / `attribution.md`. Read that file for the
current, generated breakdown - regenerate it after any scanner or exploit
change rather than trusting a stale copy.

## Why Target A skews harness-found and Target B skews manual

Target A's seeded findings are almost all "does this endpoint enforce tenant
isolation" - exactly the shape the isolation-tester was purpose-built to
replay mechanically across every endpoint × actor combination. Target B's
findings are a mix of secrets/RLS-posture (which the M5 scanners catch) and
business-logic authorization/idempotency/validation gaps (missing ownership
check on a specific route, no signature verification, no replay protection) -
these require understanding what the ROUTE is supposed to do, which is
inherently a manual-review activity; a generic scanner has no way to know
that `POST /api/bookings/[id]/cancel` is supposed to check `user_id`. This
split is deliberate and is itself part of this lab's positioning (`SPEC.md`
§6): the review isn't "just ran a scanner", and the reports say so with real
tool-attribution data, not a marketing claim.

## Fixed-mode retest methodology

Both targets ship a fixed-mode counterpart (`targets/tenant-api-fixed`,
`targets/vibe-app-fixed`) - a genuinely separate app/database/project, never
the same process as the baseline, so the baseline stays intentionally
vulnerable forever. Retest evidence is the SAME tooling re-run against the
fixed instance: the isolation-tester's same config pointed at the fixed
port (0 leaks, exit 0), the RLS checker against the fixed Supabase project
(0 FAIL), and every `exploits/*.sh` script re-run against the fixed app
(each one asserts the fixed outcome and exits non-zero if the old
vulnerability reappears - not just prose claiming it's fixed).
