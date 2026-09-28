# scanners

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

M5 (`SPEC.md` §6/§7): gitleaks (secrets), Semgrep with custom rules, a Supabase
RLS checker, and a dependency scan (Trivy) - plus an attribution script that
says, from the tools' own actual output, which findings were **tool-found**
vs **harness-found** (M2's isolation-tester) vs **manually found** (the
`exploits/*.sh` scripts). Nothing in `scanners/results/` is hand-typed;
everything is written by the scripts in this folder (CLAUDE.md).

## Layout

```
scanners/
├── rls-checker/          # the one genuinely custom analyzer here (below)
├── semgrep-rules/        # 2 custom rules + semgrep --test fixtures
├── gitleaks/             # config extending gitleaks' defaults + 3 custom rules
├── dependency-scan/      # notes; outputs are what Trivy itself writes
├── attribution/          # findings.yml (canonical list) + the script that
│                         # derives tool/harness/manual per finding
├── verify_expected.py    # CI-safe regression gate (gitleaks+semgrep+attribution;
│                         # no live Supabase needed)
└── results/              # committed tool output - regenerate, never hand-edit
```

## Supabase RLS checker (`rls-checker/`)

Finds B-03/B-04 the way a real reviewer would: by asking Postgres's own
system catalogs (`pg_class.relrowsecurity`, `pg_policies`,
`has_table_privilege`) what a table's row-level-security posture actually
is - **not** by regex-parsing the migration `.sql` files. Tables are created
in one migration and RLS/policies land in a later one; only the live,
replayed catalog state is trustworthy. See `rls_checker.py`'s module
docstring for the full classification rules and documented false negatives.

```bash
cd scanners/rls-checker
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# offline, no DB - the classification logic in isolation
.venv/bin/python -m pytest tests/test_classification.py -v

# live - needs `supabase start && supabase db reset` from targets/vibe-app/ first
.venv/bin/python rls_checker.py --expect expectations/vibe-app.baseline.yml
.venv/bin/python -m pytest tests/test_integration.py -v
```

A table with an intentionally-open policy (StudioBook's public `classes`
listing) is declared in `rls-allowlist.yml` with a reason - the checker
still **reports** it (as `ALLOWLISTED`), it just doesn't count it as a
`FAIL`. Result: `results/rls-checker/vibe-app/rls-matrix.{md,json}`.

## Semgrep custom rules (`semgrep-rules/vibe-app.yml`)

Two rules, each declaring `metadata.finding: B-xx` (the attribution script
reads this directly - see below):

- **`b01-nextpublic-service-role-key`** - a `NEXT_PUBLIC_` env var whose name
  suggests a service-role/secret credential. Name-based; can't see the
  actual value.
- **`b05-missing-ownership-check`** - a Supabase `update`/`delete` targeting
  a row by `id` with no `.eq("user_id", ...)` (or `.match({user_id: ...})`)
  anywhere in the same chain, in either order. **Documented heuristic, not a
  proof**: once RLS scopes rows by `auth.uid()` (the fixed branch), an
  unfiltered query becomes safe again - the rule's own `message` says so. It
  also (correctly, per its own stated limits) fires on
  `app/api/admin/grant-credits`, `app/api/bookings`, and
  `app/api/stripe/webhook`: all three write `credit_balance` by `id` with no
  `user_id` filter, because they run under the service-role client
  (trusted by construction as far as *this rule's specific pattern* goes -
  no missing-ownership-filter bug there). `grant-credits` is a genuinely
  useful hit for a different reason: that file *is* B-06 (a real bug -
  nothing checks the CALLER's role before granting credits) - the rule
  didn't detect B-06's actual pattern, but a human following up on the hit
  would land on a real vulnerability anyway. `bookings`/`webhook` are true
  heuristic false positives with no separate bug attached. The attribution
  script (below) does not credit B-06 from this hit - it only counts a
  rule's declared finding when the hit's file matches THAT finding's own
  evidence location.

```bash
semgrep scan --config semgrep-rules/vibe-app.yml \
  targets/vibe-app/app targets/vibe-app/components targets/vibe-app/lib \
  --no-git-ignore --json
```

Fixtures live in `semgrep-rules/fixtures/` (named that, not `tests/` -
Semgrep's own default ignore list skips paths named `test(s)`).
`semgrep --test` has a path-relation quirk with this layout, so fixtures are
verified with a plain scan + line-number assertions instead (see
`verify_expected.py`).

## gitleaks (`gitleaks/gitleaks.toml`)

Extends gitleaks' defaults (`useDefault = true`, which already catches the
Supabase service-role JWT via its builtin `jwt` rule - B-01/B-02) and adds
three rules for what the defaults miss entirely - Spring-style and bare
literal secrets have no recognizable format or entropy signature of their
own:

- **`spring-default-secret-fallback`** (A-09) - Spring's `${VAR:literal}`
  syntax on a password/secret-named key ships the literal as the real
  default whenever the env var is unset. Deliberately distinguishes this
  (bare `:`) from Docker Compose/shell's `${VAR:-default}` (`:-`) - RE2
  (Go's regexp) has no lookahead, so this uses a negated-first-character
  class instead.
- **`secret-named-key-literal-value`** (A-09, B-02) - a bare string literal
  assigned to a key whose *name* contains "secret" (YAML `:` or
  `.env`/properties `=`). Fires on both A-09's `application.yml` and B-02's
  `.env` - tagged with both ids; the attribution script (below) resolves
  each individual hit to whichever finding's own evidence location it
  actually landed in.
- **`secret-named-const-literal-value`** (B-02) - the same idea for a JS/TS
  `const`/`let`/`var` declaration, which the key:value/key=value rule above
  can't structurally match - catches `lib/stripe.ts`'s hardcoded
  `STRIPE_SECRET_KEY`.

All three key on **shape and naming**, never on the `..._DO_NOT_USE_...`
marker text this lab's fake secrets happen to carry - not circular; each
would fire identically on a real credential in the same shape. (One
regex-mechanics note worth documenting: the `$` end-of-value anchor in the
`.env`/YAML rule needs `(?im)` multiline mode, not just `(?i)` - without it
`$` only matches the end of the whole scanned chunk, so the rule would
silently catch only the last matching line in a file and miss the rest.)

A global `[allowlist]` suppresses two things: the Supabase local-CLI
**anon** key specifically (matched on its JWT payload, `"role":"anon"`) -
it's meant to be public and ships to every browser by design, so flagging
it is a false positive (scoped narrowly enough that the **service-role**
key, same `.env`, `"role":"service_role"`, is never accidentally
suppressed - that one stays a real, reportable finding); and this
scanner's own `scanners/results/` output, which necessarily quotes the same
already-fake secrets found elsewhere in the repo - without this, gitleaks
would find itself as soon as `results/gitleaks/report.json` is committed.

```bash
gitleaks git --no-banner --config scanners/gitleaks/gitleaks.toml
./scanners/gitleaks/check-tracked-env-files.sh   # the other half of B-02
```

## Dependency scan (`dependency-scan/`)

Trivy against lockfiles/manifests only (never `node_modules/`):
`targets/tenant-api/pom.xml`, `targets/tenant-api-fixed/pom.xml`,
`targets/vibe-app/package-lock.json`. Each output JSON embeds its own Trivy
version (`Trivy.Version`) and the scan's own timestamp (`CreatedAt`), so
results stay traceable to when they were generated without a separate
metadata file (not a vulnerability-DB build timestamp - Trivy's JSON
doesn't expose that field; the DB's own `UpdatedAt` is only visible in
`trivy --version`'s human-readable output).

```bash
trivy fs --scanners vuln --format json \
  --output scanners/results/dependency-scan/<target>.json <path-to-manifest>
```

These are **informational only** - not mapped to any seeded A-xx/B-xx (they
weren't seeded; they're whatever's actually outdated in the pinned
dependency versions today) and not gated in CI, since a vulnerability DB is
a moving target and yesterday's clean scan can differ from today's. Compare
`results/dependency-scan/tenant-api.json` against
`.../tenant-api-fixed.json` directly for the current counts - expect them to
look similar to each other, since M3 fixed the seeded *application* flaws,
not dependency versions.

## Attribution (`attribution/`)

`findings.yml` is the canonical A-01..A-13/B-01..B-12 list (id + title,
copied from `SPEC.md`). `build_attribution.py` decides **tool / harness /
manual** per finding from the tools' *own* actual output - never asserted
independently:

- **harness**: the id is in `results/isolation-tester/baseline`'s own
  `actual_leaks` list.
- **tool**: a scanner's own output says, in its own terms, it found this
  exact id - Semgrep via each rule's `metadata.finding`, gitleaks custom
  rules via their `tags`, gitleaks's builtin `jwt` rule resolved by reading
  the matched source line for a `NEXT_PUBLIC_` prefix (B-01) or its absence
  (B-02), and the RLS checker via its own `(schema, table, cmd)` verdict
  fields mapped to B-03/B-04.
- **manual**: neither - proven only by `targets/*/exploits/*.sh`.

An earlier version of this script used "any tool hit within N lines of the
id's own comment" - too coarse: Semgrep's `b05` rule legitimately also fires
on other privileged, similarly-shaped code in the same file as an unrelated
finding's comment (see above), which isn't evidence for *that* finding.
Reading each tool's own declared target instead of guessing by proximity
fixed it.

```bash
cd scanners/attribution
python3 -m venv .venv && .venv/bin/pip install PyYAML
.venv/bin/python build_attribution.py
```

See `results/attribution.md` for the current per-finding breakdown and
totals - generated, not repeated here by hand (this file would drift the
moment a scanner rule or exploit script changes).

## Running everything, and what CI actually gates on

```bash
# 1. RLS checker needs a live stack first:
cd targets/vibe-app && supabase start && supabase db reset && cd ../..
scanners/rls-checker/.venv/bin/python scanners/rls-checker/rls_checker.py \
  --expect scanners/rls-checker/expectations/vibe-app.baseline.yml

# 2. everything else (gitleaks, semgrep, attribution) - no live stack needed:
python3 scanners/verify_expected.py
```

CI (`scanners` job) runs the RLS checker's *pure* classification unit tests
(no DB) plus `verify_expected.py`. A baseline scan finding real, seeded
secrets/patterns is supposed to happen - CI does not gate on "zero
findings" (that would be meaningless for an intentionally-vulnerable
target), it gates on **the expected finding set matching exactly**, so a fix
that silently closes a finding, or a genuinely new unexpected one, both fail
the build. The RLS checker's live check is not in CI (needs `supabase
start`); its committed `results/rls-checker/vibe-app/rls-matrix.json` is
what `verify_expected.py`'s attribution check reads.
