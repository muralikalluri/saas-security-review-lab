# tenant-api (Target A) — LedgerLite

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

Fictional product: **LedgerLite**, invoicing for small firms. Multi-tenant B2B API.
Tenants are companies; users have roles `owner`, `admin`, `accountant`, `viewer`.

Stack: Java 21, Spring Boot 3, PostgreSQL, Keycloak.

**Status:** scaffold only (M0). This module currently exposes a health endpoint and
nothing else. The seeded vulnerabilities A-01..A-13 (`SPEC.md` §2) are added in M1.

## Run (via repo root)

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8183/actuator/health
```

## Run locally without docker

```bash
mvn -f targets/tenant-api/pom.xml spring-boot:run
```
