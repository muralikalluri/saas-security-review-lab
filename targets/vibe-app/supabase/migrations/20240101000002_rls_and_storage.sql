-- Deliberately insecure for demonstration. Do not deploy.

-- classes: a public listing, correctly readable by anyone - not a seeded flaw.
alter table public.classes enable row level security;
create policy "classes_select_all" on public.classes
    for select to authenticated, anon
    using (true);
grant select on public.classes to authenticated, anon;

-- B-04 (seeded flaw, SPEC.md B-04): RLS IS enabled on profiles, but the
-- SELECT policy is `using (true)` - every authenticated user can read
-- every OTHER user's row, including email and phone. A correct policy
-- would be `using (auth.uid() = id)`. UPDATE is scoped to the caller's own
-- row AND (not a seeded finding - kept out of scope on purpose) the column
-- grant below is restricted to profile-editing columns only, so a direct
-- PostgREST call can never self-promote role or credit_balance; those two
-- columns are only ever written server-side via the service-role client
-- (see app/api/admin/grant-credits and app/api/bookings), which is where
-- B-06 and B-10 live instead.
alter table public.profiles enable row level security;
create policy "profiles_select_any_row_b04" on public.profiles
    for select to authenticated
    using (true);
create policy "profiles_update_own_row" on public.profiles
    for update to authenticated
    using (auth.uid() = id)
    with check (auth.uid() = id);
grant select on public.profiles to authenticated;
-- Supabase's local stack applies `alter default privileges ... grant all on
-- tables` for the postgres/supabase_admin roles, so every new table
-- (including this one) starts with a blanket table-level UPDATE grant for
-- `authenticated` regardless of what we grant explicitly below. The
-- column-restricted grant is a no-op unless the blanket one is revoked
-- first - confirmed via `\dp public.profiles` showing `authenticated=arwdDxtm`
-- (full ALL) even after adding a narrower column grant on its own.
revoke update on public.profiles from authenticated;
grant update (full_name, phone, avatar_url) on public.profiles to authenticated;

-- B-03 (seeded flaw, SPEC.md B-03): row level security is never enabled on
-- bookings at all (no `alter table ... enable row level security`
-- statement anywhere - contrast with classes/profiles above). Any
-- authenticated user can read/write every OTHER user's bookings directly
-- through the PostgREST API (http://.../rest/v1/bookings), completely
-- bypassing the Next.js app's own /api routes. The explicit GRANTs below
-- are what make this deterministically reproducible via a raw curl -
-- Supabase's own "auto_expose_new_tables" default would otherwise leave
-- this dependent on project settings instead of pinned down here.
grant select, insert, update, delete on public.bookings to authenticated;

-- B-09 (seeded flaw, SPEC.md B-09): the `avatars` bucket is public with NO
-- file_size_limit and NO allowed_mime_types set (both left NULL below,
-- Supabase's own default = unrestricted) - any authenticated user can
-- upload any file type/size, including an .svg with an embedded <script>,
-- to their own path, and it is served back with the Content-Type they
-- uploaded it with, unsanitised.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('avatars', 'avatars', true, null, null)
on conflict (id) do nothing;

create policy "avatars_insert_own_path_b09" on storage.objects
    for insert to authenticated
    with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "avatars_select_public" on storage.objects
    for select to public
    using (bucket_id = 'avatars');
