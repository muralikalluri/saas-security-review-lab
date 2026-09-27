# SPEC — saas-security-review-lab

> Two deliberately vulnerable SaaS apps, a tenant-isolation testing harness that finds cross-tenant leaks automatically, and sample security reports where every finding has evidence, impact, fix, effort and a ready-to-paste AI fix prompt.

**Banner (README top and each target's README):** Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

## 1. Purpose and positioning

Public proof for two Upwork listings:

| Listing | Target in this repo | Sample deliverables |
|---|---|---|
| L4 — Multi-tenant SaaS security review with tenant isolation testing ($400 / $900 / $1,800) | **Target A:** `tenant-api` — multi-tenant B2B API (Spring Boot) | `ARCHITECTURE_REVIEW.md` (Starter), `SECURITY_REVIEW_FULL.md` (Standard/Advanced) |
| L5 — Security & code review of your AI-built app with fix plan ($150 / $400 / $900) | **Target B:** `vibe-app` — "AI-built" Next.js + Supabase + Stripe app | `RISK_SCAN_TOP10.md` (Starter), `REVIEW_WITH_FIX_PLAN.md` (Standard/Advanced) |

Both targets ship with a `fixed` branch (or `fixed/` mode) that closes every finding, so the README can show before/after.

## 2. Target A — `tenant-api` (multi-tenant B2B SaaS)

Fictional product: **"LedgerLite"** — invoicing for small firms. Tenants = companies; users have roles `owner`, `admin`, `accountant`, `viewer`.

Stack: Java 21, Spring Boot 3, Spring Security (JWT resource server), PostgreSQL (shared schema, `tenant_id` column), Keycloak for tokens, Flyway. (Java matches your positioning; the review method is language-agnostic and the report says so.)

### Seeded vulnerabilities (each becomes a finding)

| ID | Category | OWASP mapping | Seeded flaw |
|---|---|---|---|
| A-01 | Tenant isolation | API1:2023 BOLA | `GET /invoices/{id}` loads by id without tenant check |
| A-02 | Tenant isolation | API1 | `PUT /customers/{id}` updates across tenants |
| A-03 | Tenant isolation | API3 BOPLA | Invoice JSON exposes `tenantId` and internal cost fields; mass assignment lets client set `tenantId` on create |
| A-04 | Tenant isolation | API1 | Tenant taken from `X-Tenant-Id` header instead of the token |
| A-05 | Tenant isolation | A01 | Report export job builds files in shared temp path keyed by sequential id |
| A-06 | Tenant isolation | A01 | Cache key missing tenant → dashboard totals leak between tenants |
| A-07 | Function-level authz | API5 BFLA | `viewer` can call `POST /users/invite` (only checked in UI) |
| A-08 | Authentication | API2 / A07 | JWT audience not validated; long-lived tokens; no refresh rotation |
| A-09 | Secrets | A02 / A05 | Signing secret and DB password in `application.yml` committed to repo |
| A-10 | Rate limiting | API4 | No rate limit on login and invoice export |
| A-11 | Audit logging | A09 | Role changes and exports not audited; logs contain full tokens |
| A-12 | Injection | A03 | Invoice search with sort parameter concatenated into SQL |
| A-13 | SSRF | API7 | Webhook URL "test" endpoint fetches arbitrary URLs incl. metadata IP |

### Fixed mode
Tenant resolved from token only; repository layer enforces tenant (Hibernate filter or explicit `WHERE tenant_id`); Postgres RLS as defence in depth; DTOs instead of entities; `@PreAuthorize` per endpoint; rate limiting (Bucket4j); secrets from env; audit log table; parameterised sort whitelist; SSRF allow-list.

## 3. Tenant isolation test harness (`isolation-tester/`) — the headline tool

A reusable CLI (Python or Node; choose Python + pytest for readability) that:
1. Reads an OpenAPI spec + a config with two tenants × each role's credentials.
2. Creates resources as Tenant 1, then replays every endpoint/method as Tenant 2 (and as lower roles within Tenant 1) using Tenant 1's resource ids.
3. Also tests: header/tenant spoofing, mass-assignment of `tenant_id`, list endpoints for foreign rows, id enumeration.
4. Produces a matrix: endpoint × actor → expected (deny) vs actual, with request/response evidence saved as files.
5. Outputs `isolation-matrix.md` + JSON, and exits non-zero on any leak (usable in CI).

Proof in README: against Target A baseline the harness finds A-01…A-04, A-06, A-07; against fixed mode the matrix is fully green. Screenshot of both matrices.

## 4. Target B — `vibe-app` ("AI-built" SaaS)

Fictional product: **"StudioBook"** — class booking for yoga/dance studios. Built in the style typical of AI app builders: Next.js (App Router) + Supabase (Auth, Postgres, Storage) + Stripe. Runs locally with `supabase start`.

### Seeded issues (each becomes a finding)

| ID | Category | Seeded flaw |
|---|---|---|
| B-01 | Exposed keys | `SUPABASE_SERVICE_ROLE_KEY` referenced in a client component (`NEXT_PUBLIC_` prefix) |
| B-02 | Exposed keys | Stripe secret key hardcoded in a server file and committed; `.env` not in `.gitignore` |
| B-03 | DB rules | RLS disabled on `bookings` table |
| B-04 | DB rules | RLS enabled on `profiles` but policy `using (true)` |
| B-05 | Broken access control | API route checks "logged in" but not "owns record" for cancel booking |
| B-06 | Broken access control | Admin page hidden in UI but server action not role-checked |
| B-07 | Webhooks | Stripe webhook doesn't verify signature; parses JSON body directly |
| B-08 | Webhooks | No idempotency → duplicate `checkout.session.completed` grants credits twice |
| B-09 | Unsafe uploads | Avatar upload accepts any file type/size to a public bucket; SVG served inline |
| B-10 | Input validation | No server-side validation on booking form; negative quantity accepted |
| B-11 | Data exposure | Server component passes full user rows (incl. email/phone of others) to client |
| B-12 | Structure / maintainability | Supabase queries scattered in components; 600-line page file; no tests; duplicated pricing logic in client and server |

### Report format for this listing (key differentiator)

Each finding contains:
- **What's wrong** (plain English, one paragraph)
- **Why it matters** (business impact: data leak, refunds, chargebacks)
- **Evidence** (file:line, request/response, screenshot)
- **Exact fix** (code diff)
- **Effort** (S/M/L)
- **AI fix prompt** — a copy-paste prompt for Claude Code / Cursor / Lovable, scoped to the specific files, with acceptance checks. Example:

```text
In app/api/bookings/[id]/cancel/route.ts, the handler cancels any booking for any logged-in user.
Change it so it loads the booking with .eq('id', id).eq('user_id', user.id) and returns 404 if not found.
Do not change other routes. After the change, a user must not be able to cancel another user's booking;
add a test in tests/bookings.cancel.test.ts that proves this.
```

## 5. Report templates (`report-templates/`)

Shared template with: cover, scope & method, summary risk table (Critical/High/Medium/Low counts), findings (fields above), remediation plan grouped into sprints, retest notes. Pandoc → PDF with a clean style. OWASP Top 10 (2021) and OWASP API Security Top 10 (2023) IDs on every finding.

## 6. Repository layout

```
saas-security-review-lab/
├── targets/
│   ├── tenant-api/            # Spring Boot; baseline + fixed profiles or branches
│   └── vibe-app/              # Next.js + Supabase; baseline + fixed branch
├── isolation-tester/          # CLI + config examples
├── scanners/                  # scripts: gitleaks, semgrep rules, supabase RLS checker, trivy
├── report-templates/
├── sample-deliverables/
│   ├── L4-multitenant/ARCHITECTURE_REVIEW.md, SECURITY_REVIEW_FULL.md, isolation-matrix.md
│   └── L5-ai-app/RISK_SCAN_TOP10.md, REVIEW_WITH_FIX_PLAN.md
├── docker-compose.yml         # tenant-api stack (postgres, keycloak, api)
└── docs/method.md             # your review methodology (manual + automated)
```

`scanners/` shows your method isn't just tools, but uses them: gitleaks (secrets), Semgrep with custom rules (missing ownership checks, NEXT_PUBLIC service role), a small script that lists Supabase tables with RLS disabled or `using (true)` policies, Trivy/OSV for dependencies. The report states which findings were tool-found vs manually found. Most isolation findings should be manual/harness-found, which backs your "not an automated scan" claim.

## 7. Milestones for Claude Code

| M | Scope | Done when | MVP? |
|---|---|---|---|
| M0 | Repo layout, compose for Target A, CI, banners | CI green | ✅ |
| M1 | Target A baseline with A-01…A-13 | Each flaw reproducible with a curl script in `targets/tenant-api/exploits/` | ✅ |
| M2 | Isolation tester | Finds the isolation issues on baseline; JSON + Markdown matrix | ✅ |
| M3 | Target A fixed mode | Isolation matrix fully green; exploit scripts fail | ✅ |
| M4 | Target B baseline with B-01…B-12 (local Supabase) | Each issue reproducible, documented | ✅ |
| M5 | Scanners folder + Supabase RLS checker | Tool outputs saved | ✅ |
| M6 | Target B fixed branch, with the AI fix prompts actually used to fix it | Before/after in README | ✅ |
| M7 | Report templates + 4 sample deliverables + PDFs | Portfolio checklist met | ✅ |
| M8 | CI job running isolation tester against fixed mode on every push | Later | — |

Tip for M6: actually use the AI fix prompts from the report with Claude Code to fix Target B, and keep the commit history. That's live proof that the prompts work.

## 8. CLAUDE.md (copy into repo root)

```markdown
# Project: saas-security-review-lab
Read SPEC.md first. Implement only the requested milestone.

## Rules
- Baseline targets are INTENTIONALLY vulnerable. Keep every seeded flaw listed in SPEC §2 and §4 unless the milestone is a "fixed" milestone.
- Fixed versions must close every finding; the isolation tester must be fully green.
- Never use real secrets. Seeded "leaked" secrets must be obviously fake and must NOT match real key formats (e.g. FAKE_STRIPE_SECRET_DO_NOT_USE), otherwise GitHub push protection blocks the push. For Supabase use only the local CLI demo keys.
- Nothing listens on 0.0.0.0 outside docker's internal network except the demo ports; README warns against deployment.
- Each finding ID (A-xx, B-xx) appears in code comments at the flaw location and in the fix commit message.
- All companies, users and data are fictional.
```
