import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-06 (seeded flaw, SPEC.md B-06): the /admin page's UI only shows the
 * "grant credits" form to users whose profile role is 'admin' - but this
 * route, which actually performs the action, never re-checks that role
 * server-side. It writes credit_balance with the service-role client (the
 * legitimate way for a trusted server route to update a column a normal
 * user's own session cannot), so the only thing standing between any
 * logged-in user and unlimited credits for any target is the missing
 * `if (caller.role !== 'admin')` check. Any authenticated user who calls
 * this endpoint directly (bypassing the UI entirely) can grant themselves
 * - or anyone - credits.
 */
export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const { targetUserId, amount } = (await request.json()) as { targetUserId: string; amount: number };

  const supabase = createAdminClient();
  const { data: target } = await supabase.from("profiles").select("credit_balance").eq("id", targetUserId).single();
  if (!target) {
    return NextResponse.json({ error: "target user not found" }, { status: 404 });
  }

  const { data: updated, error } = await supabase
    .from("profiles")
    .update({ credit_balance: target.credit_balance + amount })
    .eq("id", targetUserId)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ profile: updated });
}
