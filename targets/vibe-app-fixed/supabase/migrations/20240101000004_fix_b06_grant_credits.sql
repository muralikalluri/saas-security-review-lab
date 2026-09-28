-- Fixed (M6). Closes the atomicity half of B-06 (SPEC.md B-06) - the
-- server-side role check itself lives in application code
-- (lib/auth/require-admin.ts), not here. This function trusts its caller
-- completely (no role check inside it), so it must only ever be reachable
-- from the already-role-checked server route, never called directly.

create or replace function public.grant_credits(p_target_user_id uuid, p_amount int)
returns public.profiles
language plpgsql
security definer
set search_path = ''
as $$
declare
  result public.profiles;
begin
  update public.profiles
  set credit_balance = credit_balance + p_amount
  where id = p_target_user_id
  returning * into strict result;

  return result;
exception
  when no_data_found then
    raise exception 'target user not found' using errcode = 'P0002';
end;
$$;

-- Supabase grants EXECUTE on every new function to PUBLIC (and therefore
-- anon/authenticated) by default - revoke that explicitly. Without this,
-- the function would be callable directly at
-- POST /rest/v1/rpc/grant_credits by anyone with a valid session, with no
-- role check at all (the RLS checker's own docs list SECURITY DEFINER
-- functions as a known false negative - it would not have caught this).
revoke execute on function public.grant_credits(uuid, int) from public, anon, authenticated;
grant execute on function public.grant_credits(uuid, int) to service_role;
