import { NextResponse } from "next/server";
import { getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * B-05 (fixed, SPEC.md B-05): the update now filters on
 * `.eq("id", id).eq("user_id", user.id).eq("status", "confirmed")` - a
 * booking that belongs to someone else, or is already cancelled, or
 * doesn't exist, all get the SAME 404, so the response can't be used to
 * probe which case it was. The service-role client is used because B-03's
 * fix revoked UPDATE on bookings from `authenticated` entirely - this
 * route is now the only place a booking can be cancelled from, and the
 * ownership check above is what makes that safe.
 */
export async function POST(request: Request, { params }: { params: { id: string } }) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  if (!UUID_RE.test(params.id)) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  const supabase = createAdminClient();
  const { data: booking, error } = await supabase
    .from("bookings")
    .update({ status: "cancelled" })
    .eq("id", params.id)
    .eq("user_id", user.id)
    .eq("status", "confirmed")
    .select()
    .single();

  if (error || !booking) {
    return NextResponse.json({ error: "not found" }, { status: 404 });
  }

  return NextResponse.json({ booking });
}
