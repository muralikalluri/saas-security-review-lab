import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { calculateCreditCost } from "@/lib/pricing";
import { isPositiveIntegerWithinBound } from "@/lib/validation";

const MAX_QUANTITY = 20;

/**
 * B-10 (fixed, SPEC.md B-10): quantity must be a positive integer within a
 * sane upper bound - rejects NaN, Infinity, floats, numeric strings, zero,
 * and negatives before it ever reaches the database. The actual booking +
 * credit debit now happens inside book_class() (see the migration), one
 * atomic statement that also re-checks capacity and balance server-side -
 * the baseline's separate select-then-update-then-insert sequence is gone,
 * along with the negative-quantity/negative-cost bug that came from it.
 *
 * B-12 (fixed, SPEC.md B-12): the cost formula itself now comes from
 * lib/pricing.ts - the one place it's defined - instead of being pasted
 * inline here a second time.
 */
export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const body = await request.json().catch(() => null);
  const classId = body?.classId;
  const quantity = body?.quantity;

  if (typeof classId !== "string") {
    return NextResponse.json({ error: "invalid classId" }, { status: 400 });
  }
  if (!isPositiveIntegerWithinBound(quantity, MAX_QUANTITY)) {
    return NextResponse.json({ error: `quantity must be a positive integer up to ${MAX_QUANTITY}` }, { status: 400 });
  }

  const supabaseAdmin = createAdminClient();
  const { data: classRow } = await supabaseAdmin.from("classes").select("credit_cost").eq("id", classId).single();
  if (!classRow) {
    return NextResponse.json({ error: "class not found" }, { status: 404 });
  }

  const creditCost = calculateCreditCost(classRow.credit_cost, quantity);

  const { data: booking, error } = await supabaseAdmin.rpc("book_class", {
    p_user_id: user.id,
    p_class_id: classId,
    p_quantity: quantity,
    p_cost: creditCost,
  });

  if (error || !booking) {
    return NextResponse.json({ error: error?.message ?? "booking failed" }, { status: 409 });
  }

  const { data: profile } = await supabaseAdmin.from("profiles").select("credit_balance").eq("id", user.id).single();

  return NextResponse.json({ booking, creditBalance: profile?.credit_balance ?? null });
}
