# AI fix prompts — StudioBook (Target B), M6

> Deliberately insecure for demonstration. Do not deploy. Run locally only.

One prompt per seeded finding (`SPEC.md` §4 format), written **before** any fix
was applied, then used (via Claude Code, against this `targets/vibe-app-fixed/`
copy) to make each fix - one commit per finding ID, in the order below (chosen
so every intermediate commit still builds and runs; see the note on B-04
breaking two read paths without B-11 landing alongside it). A handful of
prompts turned out to describe the implementation slightly differently from
what actually landed - see "Deviations during implementation" at the end of
this file rather than assuming every line below is exactly what got built;
that section is the honest record, not this one.

Each prompt assumes the *previous* prompts in the list have already landed.

---

## B-02 — Stripe secret hardcoded + `.env` committed

In `targets/vibe-app-fixed/lib/stripe.ts`, remove the hardcoded
`STRIPE_SECRET_KEY` literal. Read it from `process.env.STRIPE_SECRET_KEY` with
no fallback string, and throw at import time if it's unset, so the app fails
to start rather than silently running with no key. Add `.env` to
`targets/vibe-app-fixed/.gitignore` (remove the header comment there that says
it deliberately isn't listed) and delete the committed `targets/vibe-app-fixed/.env`
from the repo - `.env.example` is the only committed template from here on.
Do not change `targets/vibe-app/` (the baseline must keep this flaw).
Acceptance check: `git ls-files targets/vibe-app-fixed | grep -x
targets/vibe-app-fixed/.env` finds nothing; `gitleaks git --config
scanners/gitleaks/gitleaks.toml` reports no hit under `targets/vibe-app-fixed/`.

## B-01 — Service-role key shipped to the browser

In `targets/vibe-app-fixed/components/AdminUserList.tsx`, stop building a
Supabase client directly in this `"use client"` component from a
`NEXT_PUBLIC_`-prefixed service-role var. Move the user-listing query into a
new server-only module or route that uses the existing
`lib/supabase/admin.ts` `createAdminClient()` (already `server-only`-guarded),
and have this component fetch from that route instead. Remove
`NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY` from `.env`/`.env.example` entirely -
only the non-prefixed `SUPABASE_SERVICE_ROLE_KEY` should exist. Acceptance
check: `npm run build` in `targets/vibe-app-fixed`, then `grep -r
"service_role" .next/static` finds nothing.

## B-03 — RLS never enabled on `bookings`

Add a new migration `targets/vibe-app-fixed/supabase/migrations/*_fix_rls.sql`
(don't edit the baseline migrations) that enables RLS on `public.bookings` and
adds a SELECT policy scoped to `user_id = auth.uid() OR public.is_admin()`
(create `public.is_admin()` as a `SECURITY DEFINER`, `STABLE`, `SET
search_path = ''` function reading `profiles.role` for `auth.uid()` - a plain
subquery on `profiles` inside a `profiles` policy would recurse, which is what
this indirection avoids. Its EXECUTE privilege must stay granted to
`anon`/`authenticated` - Postgres evaluates an RLS policy expression AS the
connecting role, so revoking EXECUTE here would make the policy itself fail
for every real caller, not just lock the function down; that's the opposite
of what B-06/B-10's RPCs need, where EXECUTE genuinely should be
service_role-only because those trust their caller completely instead of
checking `auth.uid()` themselves). Revoke `INSERT`, `UPDATE`, `DELETE` on `bookings` from
`authenticated` - all writes happen server-side via the service-role client
or an RPC (see B-10), so a direct PostgREST write must be denied outright,
not just RLS-narrowed. Acceptance check: `scanners/rls-checker/rls_checker.py`
against this stack's DB reports 0 FAIL for `bookings`.

## B-04 — `profiles` SELECT policy is `using (true)` (+ compensating reads)

In the same new migration as B-03 (or a second one), replace
`profiles_select_any_row_b04`'s `using (true)` with `using (id = auth.uid() OR
public.is_admin())`. This will make two existing read paths silently return
empty instead of erroring - fix both in this same commit so nothing is left
broken: `app/studio/members/page.tsx` (B-11's page - do the full B-11 fix
here: read server-side with the admin client after an admin check, select
only `id, full_name`) and `app/studio/dashboard/page.tsx`'s member/booking
queries (also read via the admin client, since it's an admin-only page).
Acceptance check: `scanners/rls-checker/rls_checker.py` reports 0 FAIL for
`profiles`; `/studio/members` and `/studio/dashboard` still render real data
when visited as `noah.admin`.

## B-05 — Cancel-booking route checks login, not ownership

In `app/api/bookings/[id]/cancel/route.ts`, validate `params.id` is a UUID
(400 if not), then update via the service-role client with
`.eq("id", id).eq("user_id", user.id).eq("status", "confirmed")` - return 404
if no row was affected, whether the booking belongs to someone else or
doesn't exist (don't let the response distinguish the two). Acceptance check:
`exploits/B-05-cancel-any-booking.sh` (run against this fixed stack) shows
liam getting a 404 and maya's booking still `confirmed`.

## B-06 — Admin-only action has no server-side role check

Add a `requireAdmin()` helper (e.g. `lib/auth/require-admin.ts`) that calls
`getSessionUser()`, then looks up `profiles.role` for that user's id via the
service-role client (never trust `user_metadata`, request body, or unverified
JWT claims), returning the profile or `null`. In
`app/api/admin/grant-credits/route.ts`, call it and return 403 *before*
looking up the target user if the caller isn't an admin. Validate `amount` is
a bounded positive integer and `targetUserId` is a UUID; use an atomic
`credit_balance = credit_balance + amount` update, not read-then-write. Reuse
the same helper in `/admin` and `/studio/dashboard`'s page-level checks.
Acceptance check: `exploits/B-06-grant-credits-without-admin-role.sh` against
this stack returns 403 with liam's balance unchanged.

## B-07 — Stripe webhook never verifies its signature

In `app/api/stripe/webhook/route.ts`, read the raw body with
`await request.text()` (not `.json()`), and call
`stripe.webhooks.constructEvent(rawBody, request.headers.get("stripe-signature"),
process.env.STRIPE_WEBHOOK_SECRET)` inside a try/catch, returning 400 on any
failure (missing header, wrong secret, tampered body) without touching the
database. Fail closed (500) at import/request time if
`STRIPE_WEBHOOK_SECRET` is unset. Acceptance check:
`exploits/B-07-webhook-no-signature-check.sh` against this stack gets HTTP
400 for the unsigned forged event.

## B-08 — Webhook has no idempotency

Add a migration creating `stripe_events(event_id text primary key,
checkout_session_id text unique not null, processed_at timestamptz not null
default now())` (RLS enabled, zero policies, all grants to
anon/authenticated revoked - service_role only) and a `SECURITY DEFINER`
function `apply_checkout_credits(p_event_id text, p_session_id text,
p_user_id uuid, p_credits int) returns text` that inserts into
`stripe_events` with `on conflict (event_id) do nothing returning event_id`;
if no row came back, return `'duplicate'`; otherwise atomically run `update
profiles set credit_balance = credit_balance + p_credits where id =
p_user_id` and return `'granted'`. Revoke EXECUTE on this function from
`public`/`anon`/`authenticated`; grant only to `service_role` (Supabase
grants EXECUTE on every new function to `anon`/`authenticated` by default -
this must be explicitly revoked or the function becomes a public,
unauthenticated endpoint). In the webhook route (after B-07's signature
check), require `session.payment_status === "paid"`, validate `credits` is a
positive integer from trusted metadata, and call this RPC via the
service-role client instead of the old select-then-update. Acceptance check:
`exploits/B-08-webhook-duplicate-event-double-grant.sh`, updated to send a
correctly-signed event (via `stripe.webhooks.generateTestHeaderString`)
twice, shows the balance moving by the credit amount exactly once.

## B-09 — Avatar upload accepts any file type/size

Add a migration that `update`s (not re-`insert`s - the existing `insert ...
on conflict do nothing` would no-op against the already-seeded row) the
`avatars` bucket to set `file_size_limit` (e.g. 2 MiB) and
`allowed_mime_types` to `{image/png,image/jpeg,image/webp}` (no
`image/svg+xml`). In `components/AvatarUpload.tsx`, generate the storage path
server-side from the authenticated user's id and a fixed extension derived
from the validated MIME type (never from `file.name`). Acceptance check:
`exploits/B-09-svg-avatar-stored-xss.sh` against this stack gets a non-2xx
upload response for the SVG.

## B-10 — Booking quantity never validated server-side

Add a migration with `check (quantity > 0)` on `bookings` and `check
(credit_balance >= 0)` on `profiles`, plus a `SECURITY DEFINER` function
`book_class(p_user_id uuid, p_class_id uuid, p_quantity int, p_cost int)
returns bookings` that: locks the class row (`select ... for update`), checks
remaining capacity against confirmed bookings, checks
`credit_balance >= p_cost`, then atomically decrements the balance and
inserts the booking in one statement, raising an exception (mapped to a 4xx
by the route) if either check fails. Revoke EXECUTE from
`anon`/`authenticated`, grant only to `service_role`. In
`app/api/bookings/route.ts`, validate `quantity` is a positive integer within
a sane upper bound (reject `NaN`, floats, strings, zero, negatives) before
computing cost via the one shared `lib/pricing.ts` function (see B-12), then
call this RPC via the service-role client instead of the old
select-balance/subtract/update/insert sequence. Acceptance check:
`exploits/B-10-negative-quantity-booking.sh` against this stack returns 400
with liam's balance unchanged.

## B-11 — Server component ships full profile rows to the client

Covered as part of the B-04 commit above (the fix to `/studio/members` had to
land in the same commit as the RLS change it depends on, so the page doesn't
silently break) - see that section. This entry exists so the finding ID still
has its own row in the report; there is no separate commit for it.

## B-12 — Duplicated pricing logic, scattered queries, oversized page, no tests

In `lib/pricing.ts`, change `estimateCreditCost` so the *shared* function
validates (`quantity` must be a positive integer, throws otherwise) instead
of clamping - clamping would silently charge for 1 seat on a negative
quantity instead of rejecting it, reintroducing B-10's bug through the back
door. Give the UI its own separate display-only clamp for the *estimate
shown before submission*, clearly named and commented as UI-only, importing
the same validating function for the real calculation. Delete the two
duplicate inline formulas in `app/api/bookings/route.ts` and
`app/studio/dashboard/page.tsx` (the latter's `dashboardEstimateCreditCost`)
and import from `lib/pricing.ts` instead. Split
`app/studio/dashboard/page.tsx` into a data-loading module (e.g.
`lib/data/dashboard.ts`, one Supabase query per concern) plus several smaller
presentational components under `components/dashboard/`, so no single file
mixes fetching, aggregation and rendering at the ~600-line scale the baseline
does. Add `vitest` tests for `lib/pricing.ts` (valid/invalid quantity) and
for `book_class`'s route-level validation. Acceptance check: `rg
"credit_cost\s*\*"` matches only inside `lib/pricing.ts`; `npm test` passes;
no single file under `app/` exceeds ~150 lines.

## Deviations during implementation

A milestone review compared these prompts against the actual commits line by
line and caught a few places where what got built differs from what's written
above. Recorded here rather than silently rewriting the prompts to match the
result after the fact - the prompts above are what was actually typed and run,
this section is what happened instead:

- **B-04's prompt** says the compensating fix to `app/studio/members/page.tsx`
  should "read server-side with the admin client after an admin check". The
  page that actually landed is **auth-only** (any signed-in member can view
  it, matching the baseline's own access scope for this page/B-11's original
  finding) - it uses the service-role client to read `{id, full_name}` because
  B-04's new RLS policy would otherwise only let a member see their own row,
  not because the page is admin-restricted. It isn't.
- **B-05's prompt** says an invalid `params.id` should get a 400. The route
  that landed returns **404** for that case too, for the same reason the
  prompt itself gives for not distinguishing "someone else's booking" from
  "doesn't exist" - an invalid id is just another shape of "not found", not a
  separately-observable response.
- **B-09's prompt** says to "generate the storage path server-side". The
  upload that landed builds the path **client-side**, in
  `components/AvatarUpload.tsx`, from the MIME type validated against the
  bucket's own `allowed_mime_types` - the real, enforced security boundary is
  the bucket configuration (Supabase Storage rejects the request server-side
  regardless of what path the client asks for), not which process happens to
  concatenate the path string.
- **B-02's acceptance check** ("`gitleaks git` reports no hit under
  `targets/vibe-app-fixed/`") is not met by git HISTORY, only by the current
  tree: this module's very first commit was a verbatim copy of the baseline,
  fake secrets included, before this fix landed two commits later - `gitleaks
  git` (full-history mode) still finds that historical diff every time, by
  design. See this module's own `README.md` ("Known trade-off") for why that's
  expected and not a live finding.
- **B-08 needed a follow-up fix, not just its original prompt.** The RPC as
  first built deduped only on an exact repeated `event_id`; a milestone review
  found that a *different* event id for the *same* checkout session (a real
  shape Stripe redelivery can take) still double-granted, because the
  `on conflict (event_id)` target didn't cover the table's other unique
  constraint. Fixed in a follow-up migration
  (`20240101000008_fix_b08_conflict_target.sql`) changing it to a bare
  `on conflict do nothing`, which catches a violation of either constraint.
