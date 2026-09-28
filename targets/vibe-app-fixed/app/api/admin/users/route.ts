import { NextResponse } from "next/server";
import { createClient, getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-01 (fixed, SPEC.md B-01): the user-listing query now runs here, on the
 * server, using the service-role client from lib/supabase/admin.ts - never
 * in a "use client" component, and never from a NEXT_PUBLIC_-prefixed var.
 * The role check below is inline for now; B-06's fix extracts this same
 * check into a shared requireAdmin() helper reused by every admin route.
 */
export async function GET() {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const supabase = createClient();
  const { data: profile } = await supabase.from("profiles").select("role").eq("id", user.id).single();
  if (profile?.role !== "admin") {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }

  const admin = createAdminClient();
  const { data: users } = await admin.from("profiles").select("*");
  return NextResponse.json({ users: users ?? [] });
}
