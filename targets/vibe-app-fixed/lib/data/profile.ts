import "server-only";
import { createClient } from "@/lib/supabase/server";

/** B-12 (fixed, SPEC.md B-12): centralised, was inline in app/profile/page.tsx. */
export async function getMyProfile(userId: string) {
  const supabase = createClient();
  const { data } = await supabase.from("profiles").select("*").eq("id", userId).single();
  return data;
}
