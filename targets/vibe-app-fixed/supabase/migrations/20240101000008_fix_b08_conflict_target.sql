-- Fixed (M6). Corrects a bug in 20240101000005's apply_checkout_credits():
-- `on conflict (event_id) do nothing` only dedups an EXACT event_id repeat.
-- A DIFFERENT event id for the SAME checkout session (a real thing Stripe
-- does - e.g. a redelivered webhook can carry a new event id) hit the
-- OTHER unique constraint (checkout_session_id) instead, which isn't the
-- conflict target named here, so the insert raised a real UniqueViolation
-- instead of being treated as a duplicate - the route then returned 500
-- and Stripe would keep retrying forever. A milestone review caught this
-- live in a rolled-back transaction.
--
-- A new migration, not an edit to 20240101000005 - once a migration has
-- been applied, real deployments can't retroactively rewrite it (checksum
-- mismatch on the next `db push`); a follow-up migration is how you patch
-- a bug in an already-shipped one, same as you would in production.
--
-- Fix: `on conflict do nothing` with NO target applies to a violation of
-- ANY unique constraint/index on the table - either event_id or
-- checkout_session_id now correctly reads as "already processed".
create or replace function public.apply_checkout_credits(
    p_event_id text,
    p_session_id text,
    p_user_id uuid,
    p_credits int
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  inserted_id text;
begin
  insert into public.stripe_events (event_id, checkout_session_id)
  values (p_event_id, p_session_id)
  on conflict do nothing
  returning event_id into inserted_id;

  if inserted_id is null then
    return 'duplicate';
  end if;

  update public.profiles
  set credit_balance = credit_balance + p_credits
  where id = p_user_id;

  return 'granted';
end;
$$;

-- CREATE OR REPLACE preserves the function's OID, so the EXECUTE
-- grants/revokes from 20240101000005 still apply - re-stated here anyway
-- so this migration's own intent (service_role only) is self-evident
-- without having to cross-reference an earlier file.
revoke execute on function public.apply_checkout_credits(text, text, uuid, int) from public, anon, authenticated;
grant execute on function public.apply_checkout_credits(text, text, uuid, int) to service_role;
