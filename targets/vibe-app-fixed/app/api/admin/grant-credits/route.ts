import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/require-admin";
import { createAdminClient } from "@/lib/supabase/admin";
import { isPositiveIntegerWithinBound } from "@/lib/validation";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_GRANT_AMOUNT = 100_000;

/**
 * B-06 (fixed, SPEC.md B-06): requireAdmin() re-checks the caller's role
 * server-side and returns 403 BEFORE looking up the target user, so a
 * non-admin can't use this route's response to test whether a user id
 * exists. targetUserId/amount are validated, and the balance write is one
 * atomic SQL statement inside grant_credits() (see the migration) instead
 * of the baseline's read-balance-then-write-balance race.
 */
export async function POST(request: Request) {
  const { isAdmin } = await requireAdmin();
  if (!isAdmin) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }

  const body = await request.json().catch(() => null);
  const targetUserId = body?.targetUserId;
  const amount = body?.amount;

  if (typeof targetUserId !== "string" || !UUID_RE.test(targetUserId)) {
    return NextResponse.json({ error: "invalid targetUserId" }, { status: 400 });
  }
  if (!isPositiveIntegerWithinBound(amount, MAX_GRANT_AMOUNT)) {
    return NextResponse.json({ error: `amount must be a positive integer up to ${MAX_GRANT_AMOUNT}` }, { status: 400 });
  }

  const supabase = createAdminClient();
  const { data: updated, error } = await supabase.rpc("grant_credits", {
    p_target_user_id: targetUserId,
    p_amount: amount,
  });

  if (error || !updated) {
    return NextResponse.json({ error: error?.message ?? "target user not found" }, { status: 404 });
  }

  return NextResponse.json({ profile: updated });
}
