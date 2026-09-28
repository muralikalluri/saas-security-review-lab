# tenant-api-fixed (Target A, fixed mode)

> Deliberately insecure for demonstration. Do not deploy. Run locally only.
>
> (This banner is required in every module's README per CLAUDE.md, even
> this one - the baseline module `../tenant-api` is the one that's
> actually vulnerable. This module closes every finding it seeded.)

Fixed-mode counterpart to `../tenant-api` (SPEC.md's "Fixed mode" line for Target A).
A **separate Maven module, jar, database and Keycloak realm** - never the same process
or schema as the baseline - so the baseline stays byte-for-byte intentionally vulnerable
forever (CLAUDE.md) while this module proves every finding A-01..A-13 is closeable.

## Run (via repo root)

```bash
cp .env.example .env
docker compose up -d --build api-fixed
curl http://localhost:8184/actuator/health
```

Re-run any script in `../tenant-api/exploits/` against this instance:

```bash
API_BASE=http://localhost:8184 ../tenant-api/exploits/A-01-bola-invoice-by-id.sh
# A-08 and A-11 need a couple of extra overrides - see that folder's README.
```

Or run the isolation-tester's SAME config against this instance:

```bash
cd ../../isolation-tester
API_BASE=http://localhost:8184 .venv/bin/python -m isolation_tester run \
  --config config/tenant-api.baseline.yaml \
  --openapi openapi/tenant-api.isolation.yaml \
  --run-name fixed \
  --expect expectations/tenant-api.fixed.yaml
# Should exit 0 (matches expectations/tenant-api.fixed.yaml's empty leak set).
# See the generated results/isolation-tester/fixed/isolation-matrix.md for
# the actual, current result - never trust this comment over that file.
```

## What changed, per finding

| ID | Fix |
|---|---|
| A-01 | `InvoiceRepository.findByIdAndTenantId` - explicit WHERE, not just load-by-id |
| A-02 | `CustomerRepository.findByIdAndTenantId`, same pattern, for the PUT |
| A-03 | `tenantId` removed from `InvoiceCreateRequest`/`InvoiceResponse`/`InvoiceRow` entirely (BOPLA); a `customerId` outside the caller's own tenant is rejected (400) |
| A-04 | `TenantContext` no longer reads any header at all - JWT `tenant_id` claim only, and a missing claim is a 403, not a silent fallback |
| A-05 | `ExportService.read(id, callerTenantId)` compares ownership; per-tenant export subdirectories |
| A-06 | Dashboard cache key is `"summary:" + tenantId`, not a constant |
| A-07 | `@EnableMethodSecurity` + `@PreAuthorize` per endpoint; invite is owner/admin-only and can't grant `owner` |
| A-08 | JWT audience is validated (`aud` must contain `tenant-api`); the realm issues 5-minute access tokens and rejects refresh-token reuse |
| A-09 | No hardcoded DB password anywhere in `application.yml`; the app fails to start without `DB_PASSWORD` set via env, and its own runtime credential is a separate, unprivileged role (see RLS below) |
| A-10 | Bucket4j rate limiting on `/auth/login` (per username) and `/invoices/export` (per tenant) |
| A-11 | An `audit_log` table records invites and exports, written in the SAME transaction as the action; `RequestLoggingFilter` never logs the Authorization header's value |
| A-12 | `sort` is checked against a column-name whitelist before being placed in `ORDER BY` |
| A-13 | Webhook test requires https + a static per-deployment host allow-list + no IP literals + redirects disabled, checked BEFORE any outbound call |

## Postgres Row-Level Security (defence in depth)

On top of every explicit `WHERE tenant_id = ?` above, `V3__row_level_security.sql`
creates a separate, unprivileged `ledgerlite_app` role (the app's actual runtime
connection - Flyway itself still runs as the table-owning role) and RLS policies on
`customers`/`invoices`/`invites`/`audit_log` comparing `tenant_id` to
`current_setting('app.tenant_id', true)`. That session variable is set with
`set_config(..., true)` (transaction-local, i.e. exactly `SET LOCAL`) as the FIRST
statement of every transaction, via `TenantScope.call/run` (see its Javadoc) - never a
plain `SET`, which would leak across a pooled connection into the next, unrelated
request. Forgetting to go through `TenantScope` fails **closed** (an empty result,
because `current_setting` returns NULL when unset and `tenant_id = NULL` is never
true), never open.

## Tests

```bash
mvn -f targets/tenant-api-fixed/pom.xml verify
```

Same Testcontainers-Postgres + spring-security-test approach as the baseline module
(`TenantIsolationFixedTest`) - proves the fixes hold, plus the missing-tenant-claim and
role-matrix invariants that only exist in this module.
