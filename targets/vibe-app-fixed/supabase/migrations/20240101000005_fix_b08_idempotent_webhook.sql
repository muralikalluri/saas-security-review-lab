-- Fixed (M6). Closes B-08 (SPEC.md B-08).

-- Records every Stripe event id we've ever processed. RLS enabled with
-- zero policies and all default grants revoked - this table is never
-- meant to be reachable from anon/authenticated at all, only from the
-- webhook route via the service-role client (which bypasses RLS, but the
-- revoked grants are a second, independent barrier against direct
-- PostgREST access - same "every new table starts wide open" gotcha
-- fixed on profiles/bookings elsewhere in this migration series).
create table public.stripe_events (
    event_id text primary key,
    checkout_session_id text not null unique,
    processed_at timestamptz not null default now()
);
alter table public.stripe_events enable row level security;
revoke all on public.stripe_events from anon, authenticated;

-- Atomically records the event (or detects a duplicate) AND grants
-- credits, in one statement block - a single PostgREST RPC call is one
-- transaction, so there is no window where the event is marked processed
-- but the credit grant didn't happen (or vice versa). The primary key on
-- event_id also serialises concurrent deliveries of the SAME event: the
-- second `insert` waits on the first's row lock, then hits the conflict.
--
-- Returns 'granted' or 'duplicate' - never raises for a duplicate, so the
-- webhook route can still return Stripe a 2xx (telling it to stop
-- retrying) instead of an error.
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
  on conflict (event_id) do nothing
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

-- Supabase grants EXECUTE on every new function to PUBLIC (and therefore
-- anon/authenticated) by default - revoke that. This function trusts its
-- caller completely (no signature/session check inside it - that already
-- happened in the route before calling this), so it must only ever be
-- reached from the webhook route's service-role client.
revoke execute on function public.apply_checkout_credits(text, text, uuid, int) from public, anon, authenticated;
grant execute on function public.apply_checkout_credits(text, text, uuid, int) to service_role;
