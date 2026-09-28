# vibe-app-fixed (Target B, fixed mode)

> Deliberately insecure for demonstration and training. Do not deploy. Run locally only.
>
> (This banner is required in every module's README per CLAUDE.md, even this one -
> the baseline module `../vibe-app` is the one that's actually vulnerable. This
> module closes every finding it seeded.)

Fixed-mode counterpart to `../vibe-app` (SPEC.md's "fixed branch" line for Target
B). A **separate Next.js app and a separate local Supabase project** (its own
`project_id`, its own ports) - never the same process or database as the
baseline - so `../vibe-app` stays byte-for-byte intentionally vulnerable forever
(CLAUDE.md) while this module proves every finding B-01..B-12 is closeable.

Built with `AI_FIX_PROMPTS.md` in this directory: one prompt per finding,
written before any fix, then applied one at a time - **one commit per finding
ID** (`git log --oneline` in this repo shows the sequence). That's the literal
answer to SPEC.md §7's M6 instruction to "actually use the AI fix prompts...
with Claude Code to fix Target B, and keep the commit history."

## Run

```bash
# from the repo root
cd targets/vibe-app-fixed
cp .env.example .env   # fill in ANON_KEY/SERVICE_ROLE_KEY from `supabase start`'s own output
supabase start
npm install
npm run dev
# visit http://localhost:8193
```

Host ports (8193 Next.js, 8194 Supabase API, 8195 Postgres, 8196 shadow DB, 8197
Studio, 8198 Mailpit) are the baseline's ports +6, all in the 81xx range per
CLAUDE.md, set in `supabase/config.toml` and the repo root `.env.example`. Both
stacks can run at the same time.

## Verify: the full exploit suite, run against THIS stack

```bash
cd exploits
for f in B-*.sh; do echo; echo "##### $f #####"; ./"$f" || true; done
```

Every script is the **same file** as `../vibe-app/exploits/`, adapted to assert
the fixed outcome (each one exits non-zero if the old vulnerable behaviour
reappears) and pointed at this app's own ports by default. Current result,
against a freshly `supabase db reset` stack: **all 12 report FIXED, exit 0.**

```bash
# RLS checker (M5) against this stack:
cd ../../../  # repo root
scanners/rls-checker/.venv/bin/python scanners/rls-checker/rls_checker.py \
  --dsn "postgresql://postgres:postgres@127.0.0.1:8195/postgres" \
  --target-dir targets/vibe-app-fixed --run-name vibe-app-fixed
# 0 FAIL - see scanners/results/rls-checker/vibe-app-fixed/rls-matrix.md
# (never trust this comment over that generated file)
```

## What changed, per finding

| ID | Fix |
|---|---|
| B-01 | Service-role key moved server-only: `app/api/admin/users/route.ts` uses `lib/supabase/admin.ts`'s `createAdminClient()`; `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY` removed entirely |
| B-02 | `lib/stripe.ts` reads `STRIPE_SECRET_KEY` from env with no fallback (throws if unset); `.env` gitignored and untracked |
| B-03 | RLS enabled on `bookings`; `INSERT`/`UPDATE`/`DELETE` explicitly revoked from `authenticated` (Supabase's default ACLs grant them on every new table) - every write goes through a service-role route or RPC |
| B-04 | `profiles`' `using (true)` SELECT policy replaced with `id = auth.uid() or is_admin()`; `is_admin()` is a `SECURITY DEFINER` function (avoids the self-referential-policy recursion a plain subquery would hit) |
| B-05 | `POST /api/bookings/[id]/cancel` filters on `id`, `user_id = caller`, and `status = 'confirmed'`; a UUID-shaped, someone-else's, or already-cancelled id all return the same 404 |
| B-06 | New `lib/auth/require-admin.ts`, shared by every admin route/page; `grant_credits()` is a `SECURITY DEFINER` RPC (atomic, `EXECUTE` restricted to `service_role`) |
| B-07 | `stripe.webhooks.constructEvent()` against the raw body and `stripe-signature` header; any failure is 400 before the payload is ever parsed |
| B-08 | `stripe_events(event_id primary key)` + `apply_checkout_credits()`, one atomic RPC - a replayed event id is a no-op |
| B-09 | `avatars` bucket's `allowed_mime_types` restricted to png/jpeg/webp with a 2 MiB cap; stored filename's extension comes from the validated type, never the raw `file.name` |
| B-10 | `book_class()` RPC: locks the class row, re-checks capacity and balance, debits credits and inserts the booking atomically; quantity validated as a bounded positive integer first |
| B-11 | `app/studio/members/page.tsx` selects only `{id, full_name}` - fixed in the SAME commit as B-04, since B-04's RLS change would otherwise have silently broken this page's read |
| B-12 | One pricing formula (`lib/pricing.ts`, validates rather than clamps), one data module (`lib/data/dashboard.ts`), the ~600-line dashboard page split into 13 components under `components/dashboard/` (largest `app/` file is now 83 lines), and `vitest` tests added (`lib/pricing.test.ts`, `lib/validation.test.ts`) |

Every fix keeps the corresponding app-level check even where RLS now also
covers it (e.g. B-05's ownership check, B-06's role check) - RLS only
protects direct PostgREST access; every write path here goes through the
service-role client or a `SECURITY DEFINER` RPC specifically because it
bypasses RLS, so the application-level check is the only thing standing
between an authenticated caller and that write. Same defence-in-depth
pattern as Target A's fixed mode.

## Tests

```bash
npm test    # vitest - lib/pricing.test.ts, lib/validation.test.ts
```

Wired up since M4 with no spec files; M6's B-12 fix is what actually adds
tests, covering exactly the NaN/Infinity/float/negative shapes B-10 came from.

## Known trade-off: this module's OWN early git history

The very first commit on this module (`chore: M6 setup`) is a verbatim copy of
the baseline, so it necessarily includes the baseline's own fake secrets in
its diff before any fix landed - `gitleaks git` (which scans full history)
still finds them there, even though the CURRENT working tree is clean (checked
by `exploits/B-02-secrets-committed.sh` and confirmed via `gitleaks dir` /
`git ls-files`). In a real rotation-driven incident response this is exactly
the case for rotating the credential rather than trusting history rewrite -
noted here rather than hidden.
