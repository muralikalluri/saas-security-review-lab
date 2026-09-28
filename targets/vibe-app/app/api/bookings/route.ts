import { NextResponse } from "next/server";
import { createClient, getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const body = await request.json();
  const { classId, quantity } = body as { classId: string; quantity: number };

  const supabase = createClient();
  const { data: classRow } = await supabase.from("classes").select("credit_cost").eq("id", classId).single();
  if (!classRow) {
    return NextResponse.json({ error: "class not found" }, { status: 404 });
  }

  // B-10 (seeded flaw, SPEC.md B-10): `quantity` is used exactly as
  // received - no check that it is a positive integer, or that it fits
  // the class's remaining capacity.
  //
  // B-12 (seeded flaw, SPEC.md B-12): this duplicates
  // lib/pricing.ts's estimateCreditCost formula instead of importing it,
  // and - unlike the client's display copy - has no Math.max(1, ...)
  // clamp, so a negative quantity produces a NEGATIVE credit cost.
  // Combined with B-10, a booking with quantity=-5 subtracts a negative
  // number from credit_balance, i.e. INCREASES it.
  const creditCost = classRow.credit_cost * quantity;

  // credit_balance is written with the service-role client: a normal
  // user's own session grant only covers profile-editing columns (see
  // supabase/migrations/20240101000002_rls_and_storage.sql), so this
  // route - not the client - is the trusted place that debits credits.
  const supabaseAdmin = createAdminClient();
  const { data: profile } = await supabaseAdmin.from("profiles").select("credit_balance").eq("id", user.id).single();
  if (!profile) {
    return NextResponse.json({ error: "profile not found" }, { status: 404 });
  }

  const newBalance = profile.credit_balance - creditCost;

  const { error: updateError } = await supabaseAdmin.from("profiles").update({ credit_balance: newBalance }).eq("id", user.id);
  if (updateError) {
    return NextResponse.json({ error: updateError.message }, { status: 500 });
  }

  const { data: booking, error: bookingError } = await supabase
    .from("bookings")
    .insert({ user_id: user.id, class_id: classId, quantity })
    .select()
    .single();
  if (bookingError) {
    return NextResponse.json({ error: bookingError.message }, { status: 500 });
  }

  return NextResponse.json({ booking, creditBalance: newBalance });
}
