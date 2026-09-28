# vibe-app (Target B) — StudioBook

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.

Fictional product: **StudioBook**, class booking for yoga/dance studios. Built in the
style typical of AI app builders: Next.js 14 (App Router) + Supabase (Auth, Postgres,
Storage) + Stripe. Runs entirely locally via `supabase start` - no cloud project, no
real Stripe account needed to reproduce any seeded finding.

**Status:** M4 baseline. All 12 seeded issues B-01..B-12 (`SPEC.md` §4) are present
and reproducible; see `exploits/` for one script per finding. This is the
intentionally-vulnerable baseline - the fixed branch lands in M6.

## Run

```bash
# from the repo root
cd targets/vibe-app
supabase start
npm install
npm run dev
# visit http://localhost:8187 - see exploits/README.md for demo users/password
```

`supabase start` prints the local `ANON_KEY`/`SERVICE_ROLE_KEY` - these are the
well-known Supabase CLI local-dev demo keys (identical on every `supabase init`
anywhere), already baked into the committed `.env` (see B-02) and
`exploits/_common.sh`. Host ports (8187 Next.js, 8188 Supabase API, 8189 Postgres,
8190 Studio, 8191 Mailpit) are all in the 81xx range per CLAUDE.md and set in
`supabase/config.toml` / the repo root `.env.example`.

## Seeded findings

| ID | What | Where |
|---|---|---|
| B-01 | Service-role key shipped to the browser via a `NEXT_PUBLIC_` var | `components/AdminUserList.tsx` |
| B-02 | Stripe secret hardcoded + `.env` committed | `lib/stripe.ts`, `.env` |
| B-03 | RLS never enabled on `bookings` | `supabase/migrations/20240101000002_rls_and_storage.sql` |
| B-04 | `profiles` SELECT policy is `using (true)` | same migration |
| B-05 | Cancel-booking route checks login, not ownership | `app/api/bookings/[id]/cancel/route.ts` |
| B-06 | Admin-only action has no server-side role check | `app/api/admin/grant-credits/route.ts` |
| B-07 | Stripe webhook never verifies its signature | `app/api/stripe/webhook/route.ts` |
| B-08 | Webhook has no idempotency - replay double-grants credits | same file |
| B-09 | Avatar upload accepts any file type/size to a public bucket | `supabase/migrations/...`, `components/AvatarUpload.tsx` |
| B-10 | Booking quantity is never validated server-side | `app/api/bookings/route.ts` |
| B-11 | Server component ships full profile rows (incl. phone) to the client | `app/studio/members/page.tsx` |
| B-12 | Duplicated pricing logic (3 copies), queries scattered per-page, ~600-line page, no tests | `lib/pricing.ts`, `app/api/bookings/route.ts`, `app/studio/dashboard/page.tsx` |

Every finding ID appears as a code comment at its actual flaw location (CLAUDE.md).

## A known, accepted trade-off

`npm audit` reports several Next.js framework-level advisories even on the current
`14.2.x` patch line (the actual fixed version per the advisory database is a `16.x`
major bump, which would require reworking several async-API changes across this
codebase). These are ambient dependency-hygiene findings a real dependency scanner
(M5) would also surface - they are NOT among, and should not be confused with, the
12 seeded B-xx findings this module exists to demonstrate. See M5's scanner output
for how the report distinguishes the two.

## Tests

No automated test suite for this milestone (M4 is the baseline; SPEC's acceptance
criterion is "each issue reproducible, documented" - see `exploits/`). `npm test`
(vitest) is wired up for M6's fixed branch.
