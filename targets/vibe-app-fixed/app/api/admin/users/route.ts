import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/require-admin";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-01 (fixed, SPEC.md B-01): the user-listing query runs here, on the
 * server, using the service-role client from lib/supabase/admin.ts - never
 * in a "use client" component, and never from a NEXT_PUBLIC_-prefixed var.
 * B-06 (fixed, SPEC.md B-06): the role check uses the same requireAdmin()
 * helper every admin route/page shares.
 */
export async function GET() {
  const { isAdmin } = await requireAdmin();
  if (!isAdmin) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }

  const admin = createAdminClient();
  const { data: users } = await admin.from("profiles").select("*");
  return NextResponse.json({ users: users ?? [] });
}
