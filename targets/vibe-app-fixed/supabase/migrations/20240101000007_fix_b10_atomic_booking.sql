-- Fixed (M6). Closes B-10 (SPEC.md B-10).

-- Defence in depth: even a direct (service-role) write can't put these
-- tables into a nonsensical state.
alter table public.bookings add constraint bookings_quantity_positive check (quantity > 0);
alter table public.profiles add constraint profiles_credit_balance_nonnegative check (credit_balance >= 0);

-- Atomically checks capacity and balance, then debits credits and inserts
-- the booking - all in one statement block, so there is no window between
-- "checked" and "wrote" for a concurrent request to race through. Locks
-- the class row (`for update`) so two concurrent bookings for the last
-- seat can't both pass the capacity check before either commits.
create or replace function public.book_class(
    p_user_id uuid,
    p_class_id uuid,
    p_quantity int,
    p_cost int
)
returns public.bookings
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_capacity int;
  v_booked int;
  v_balance int;
  result public.bookings;
begin
  if p_quantity <= 0 then
    raise exception 'quantity must be a positive integer' using errcode = '22023';
  end if;

  select capacity into v_capacity from public.classes where id = p_class_id for update;
  if not found then
    raise exception 'class not found' using errcode = 'P0002';
  end if;

  select coalesce(sum(quantity), 0) into v_booked
  from public.bookings
  where class_id = p_class_id and status = 'confirmed';

  if v_booked + p_quantity > v_capacity then
    raise exception 'class is at capacity' using errcode = '23514';
  end if;

  select credit_balance into v_balance from public.profiles where id = p_user_id for update;
  if v_balance is null or v_balance < p_cost then
    raise exception 'insufficient credits' using errcode = '23514';
  end if;

  update public.profiles set credit_balance = credit_balance - p_cost where id = p_user_id;

  insert into public.bookings (user_id, class_id, quantity)
  values (p_user_id, p_class_id, p_quantity)
  returning * into result;

  return result;
end;
$$;

-- Supabase grants EXECUTE on every new function to PUBLIC (and therefore
-- anon/authenticated) by default - revoke that. This function trusts its
-- caller completely (the quantity/cost validation happens in the route
-- before calling it), so it must only ever be reached from there.
revoke execute on function public.book_class(uuid, uuid, int, int) from public, anon, authenticated;
grant execute on function public.book_class(uuid, uuid, int, int) to service_role;
