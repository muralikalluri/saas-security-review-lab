# isolation-tester

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

A reusable CLI that finds cross-tenant leaks automatically (`SPEC.md` section 3).
Reads an OpenAPI subset + a tenants/roles/fixtures config, replays every declared
endpoint as the "wrong" actor (a foreign tenant, a lower role, a spoofed header,
mass-assigned `tenantId`, walked ids), and writes an `isolation-matrix.md` +
`isolation-matrix.json` with request/response evidence for every probe. Exits
non-zero on a leak, so it's usable as a CI gate.

## Why pytest

The probes themselves are ordinary pytest tests (parametrized at collection time
from the OpenAPI+config combination), run serially, one process. That gives:
per-probe evidence + human-readable pass/fail output for free, and a
`pytest_sessionfinish` hook that aggregates every result into the matrix and
sets the process exit code itself (see "Exit code policy" below) - independent
of pytest's own PASSED/FAILED count, which stays useful for a human skimming a
terminal (a **LEAK** row on baseline shows up as a "FAILED" test, which is
exactly what you want to see when running this against a target that's
supposed to be vulnerable).

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# against the running baseline stack (see ../targets/tenant-api and
# ../docker-compose.yml - `docker compose up -d --build` from the repo root first)
.venv/bin/python -m isolation_tester run \
  --config config/tenant-api.baseline.yaml \
  --openapi openapi/tenant-api.isolation.yaml \
  --run-name baseline \
  --expect expectations/tenant-api.baseline.yaml

# once Target A's fixed profile exists (M3):
.venv/bin/python -m isolation_tester run \
  --config config/tenant-api.baseline.yaml \
  --openapi openapi/tenant-api.isolation.yaml \
  --run-name fixed \
  --expect expectations/tenant-api.fixed.yaml
```

`API_BASE` env var overrides the config's `base_url` (e.g. to point at a fixed-mode
instance on a different port without a second config file).

Output: `<repo root>/results/isolation-tester/<run-name>/isolation-matrix.{md,json}`
plus per-probe request/response evidence under `raw/` (gitignored - regenerate by
re-running; the matrix files themselves ARE committed, per CLAUDE.md: never
hand-type these numbers, always regenerate them).

## Exit code policy

- **0** - the actual leaked-finding set matches `--expect` exactly (or, run without
  `--expect`, simply: no leaks and no errors).
- **1** - a leak that wasn't expected, OR an expected leak went missing (baseline
  quietly stopped finding something - a regression, not "good news").
- **2** - the run itself isn't trustworthy: a login failed, `/api/status` was
  unreachable, or a positive control failed (an actor couldn't read their OWN
  resource). Never conflate this with "0 leaks found" - a down API must not look
  like a secure API.

## What this harness does NOT probe, and why

Per `SPEC.md` section 3, the harness is expected to (re)discover A-01, A-02, A-03,
A-04, A-06, A-07 on Target A's baseline. This build also probes A-05 (export
download by sequential id - a textbook BOLA/id-enumeration case, deliberately
NOT excluded, see design notes below) via `GET /invoices/exports/{id}`.

A-08 through A-13 are declared out of scope in
`config/tenant-api.baseline.yaml`'s `excluded_findings` list, each with a reason -
none of them are expressible as "actor X gets denied a resource Y owns/doesn't
own" (JWT lifetime, secrets in a committed file, absent rate limiting, absent
audit logs, SQL injection that stays tenant-scoped, SSRF). They're proven
instead by the curl scripts in `targets/tenant-api/exploits/`.

## Layout

```
isolation_tester/         # the package: config/openapi loading, HTTP client,
                           # oracle (deny/leak classifier), matrix writer
openapi/                   # hand-authored OpenAPI SUBSET with x-tenant-isolation
                           # vendor extensions naming probe types + finding ids
config/                    # tenants x roles x fixture ids per profile
expectations/              # expected-leak sets per profile (baseline vs fixed)
tests/                     # the actual probes (live, hit a real API)
unit_tests/                # offline, mocked, no network - what CI runs (oracle
                           # polarity + exit-code policy correctness)
```

## Design notes / invariants (why the oracle is shaped this way)

- **A single-resource GET/PUT is either DENIED (403/404) or a LEAK (any 2xx) -
  never anything else.** A 401/5xx is an ERROR, not evidence of correct
  isolation - an API that's down must never look "secure".
- **Positive controls are mandatory and run first.** Every actor must be able to
  read their OWN resources before any deny/leak probe runs. Without this, a
  broken/down API - or an over-aggressive "fix" that blocks everyone, not just
  foreign tenants - would show a fully green matrix. A failed control forces
  exit code 2, not 0.
- **The dashboard's cache-order (A-06) and header-spoof (A-04) checks are
  hand-sequenced, not generically parametrized**, because they're the one place
  in this API where two flaws are causally entangled (the tenant used to
  populate the cache depends on the spoofable header, and the cache then hides
  that from the next caller for up to `cache_ttl_seconds`). See
  `tests/test_01_dashboard.py`.
- **A-01/A-02 stay independent of the header-spoof mechanism.** `TenantContext`
  (the spoofable component) is only used by list/aggregate endpoints; the
  single-resource BOLA endpoints bypass it entirely. This means fixing A-04 in
  M3 cannot accidentally "fix" A-01/A-02 too, and vice versa.
- **Mutating probes run last** (`order_phase` marker, see `conftest.py`), and
  `bola-write` (A-02) restores the original values immediately after any
  successful write, so re-running this suite - or the exploit scripts - against
  the same long-lived baseline stack stays reproducible.
