-- Fixed (M6). Closes B-03 and B-04 (SPEC.md).
--
-- A new migration, not an edit to 20240101000002 - the diff between the two
-- files IS the before/after for this finding.

-- Used by both fixed policies below. SECURITY DEFINER + a pinned empty
-- search_path so it can read public.profiles regardless of the calling
-- role's own (now-restrictive) RLS, without being hijackable via a
-- session-local search_path. STABLE, not VOLATILE, since it only reads.
-- A plain subquery on profiles INSIDE a profiles policy would recurse -
-- this indirection is what avoids that.
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles where id = auth.uid() and role = 'admin'
  );
$$;

-- B-04 (fixed, SPEC.md B-04): replace the `using (true)` SELECT policy -
-- every authenticated user could read every other user's email/phone -
-- with one scoped to the caller's own row, or an admin.
drop policy if exists "profiles_select_any_row_b04" on public.profiles;
create policy "profiles_select_own_row_or_admin" on public.profiles
    for select to authenticated
    using (id = auth.uid() or public.is_admin());

-- B-03 (fixed, SPEC.md B-03): enable RLS (it was never enabled at all) and
-- add an owner/admin SELECT policy. Also revoke INSERT/UPDATE/DELETE from
-- `authenticated` outright, on top of RLS - every booking write happens
-- server-side via the service-role client or a SECURITY DEFINER RPC (see
-- the B-05/B-10 migrations), so a direct PostgREST write must be denied at
-- the privilege layer, not merely RLS-narrowed. Supabase's default ACLs
-- already granted `authenticated` blanket insert/update/delete on this
-- table at CREATE TABLE time (the same "every new table starts wide open"
-- gotcha fixed on profiles in M4) - explicit revoke is required, enabling
-- RLS alone would NOT remove that pre-existing grant.
alter table public.bookings enable row level security;
revoke insert, update, delete on public.bookings from authenticated;
create policy "bookings_select_own_row_or_admin" on public.bookings
    for select to authenticated
    using (user_id = auth.uid() or public.is_admin());
