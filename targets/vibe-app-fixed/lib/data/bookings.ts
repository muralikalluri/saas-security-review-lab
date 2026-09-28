import "server-only";
import { createClient } from "@/lib/supabase/server";

/** B-12 (fixed, SPEC.md B-12): centralised, was inline in app/bookings/page.tsx. */
export async function listMyBookings(userId: string) {
  const supabase = createClient();
  const { data } = await supabase
    .from("bookings")
    .select("id, quantity, status, classes(title, starts_at)")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  return data ?? [];
}
