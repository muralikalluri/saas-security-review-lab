-- Fixed (M6), defence in depth. book_class() trusts its caller's p_cost
-- (the route computes it via lib/pricing.ts's calculateCreditCost(), which
-- already throws on a non-positive-integer quantity before this function
-- is ever reached) - but a SECURITY DEFINER function that's ever called
-- from anywhere else should not rely solely on the caller having validated
-- correctly. A milestone review flagged that a negative p_cost, called
-- directly, currently INCREASES the balance instead of erroring.
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
  if p_cost < 0 then
    raise exception 'cost must not be negative' using errcode = '22023';
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

revoke execute on function public.book_class(uuid, uuid, int, int) from public, anon, authenticated;
grant execute on function public.book_class(uuid, uuid, int, int) to service_role;
