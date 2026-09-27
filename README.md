# saas-security-review-lab

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

Two deliberately vulnerable SaaS apps, a tenant-isolation testing harness that finds
cross-tenant leaks automatically, and sample security reports where every finding has
evidence, impact, fix, effort and a ready-to-paste AI fix prompt.

**Status: work in progress.** This README is a scaffold and will be regenerated from
actual results once the full MVP (milestones M0–M7, see `SPEC.md`) is complete.

## Targets

| Target | Product (fictional) | Stack | Status |
|---|---|---|---|
| `targets/tenant-api` | LedgerLite — multi-tenant invoicing API | Java 21, Spring Boot 3, PostgreSQL, Keycloak | scaffold only (M0) |
| `targets/vibe-app` | StudioBook — class booking app | Next.js, Supabase, Stripe | not started |

## Repository layout

See `SPEC.md` §6 for the full target layout and `SPEC.md` §7 for the milestone plan.

## Quickstart (Target A scaffold)

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8183/actuator/health
docker compose down -v
```

## Documentation

- [`SPEC.md`](SPEC.md) — full specification, seeded findings, milestone plan
- [`docs/method.md`](docs/method.md) — review methodology (manual + automated)
