# tenant-api (Target A) — LedgerLite

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

Fictional product: **LedgerLite**, invoicing for small firms. Multi-tenant B2B API.
Tenants are companies; users have roles `owner`, `admin`, `accountant`, `viewer`.

Stack: Java 21, Spring Boot 3, PostgreSQL (Flyway-managed), Keycloak (JWT resource server).

**Status:** M1 baseline. All 13 seeded vulnerabilities A-01..A-13 (`SPEC.md` §2) are
present and reproducible; see `exploits/` for one curl script per finding. This is the
intentionally-vulnerable baseline profile - the fixed mode lands in M3.

## Run (via repo root)

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8183/actuator/health
# then see exploits/README.md to reproduce every seeded flaw
```

Keycloak (realm `ledgerlite`) auto-imports `keycloak/ledgerlite-realm.json` on
first start - two fictional tenants, four roles, six lab users. Postgres runs the
Flyway migrations in `src/main/resources/db/migration/` on API startup, seeding
deterministic fixture rows for both tenants.

## Run locally without docker

```bash
mvn -f targets/tenant-api/pom.xml spring-boot:run
```

Needs `DB_URL`/`DB_USER`/`DB_PASSWORD` and `KEYCLOAK_JWK_SET_URI`/
`KEYCLOAK_INTERNAL_TOKEN_URI` pointed at a running Postgres + Keycloak (the
docker-compose defaults assume the containers, not localhost - override them).

## Tests

```bash
mvn -f targets/tenant-api/pom.xml verify
```

Integration tests spin up a real Postgres via Testcontainers (Flyway runs for real)
and use `spring-security-test`'s JWT support to simulate both tenants/roles without
needing a live Keycloak - see `src/test/java/.../TenantIsolationFlawsTest.java`.
