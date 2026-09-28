import { NextResponse } from "next/server";
import { createClient, getSessionUser } from "@/lib/supabase/server";

/**
 * B-05 (seeded flaw, SPEC.md B-05): checks that the caller is logged in,
 * but never checks that the booking being cancelled belongs to them - any
 * authenticated user can cancel ANY booking by id. The service-role-free
 * `createClient()` used here would normally be stopped by RLS, but
 * bookings has none (B-03), so this reaches the database unguarded twice
 * over.
 */
export async function POST(request: Request, { params }: { params: { id: string } }) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const supabase = createClient();
  const { data: booking, error } = await supabase
    .from("bookings")
    .update({ status: "cancelled" })
    .eq("id", params.id)
    .select()
    .single();

  if (error || !booking) {
    return NextResponse.json({ error: error?.message ?? "not found" }, { status: 404 });
  }

  return NextResponse.json({ booking });
}
