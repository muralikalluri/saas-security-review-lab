import "server-only";
import { createClient } from "@/lib/supabase/server";

/**
 * B-12 (fixed, SPEC.md B-12): classes queries centralised here instead of
 * written inline in app/page.tsx and app/classes/[id]/page.tsx - the
 * "queries scattered in components" half of this finding, not just the
 * dashboard's pricing/data-layer half.
 */
export async function listUpcomingClasses() {
  const supabase = createClient();
  const { data } = await supabase
    .from("classes")
    .select("id, title, instructor, studio_name, capacity, price_cents, credit_cost, starts_at")
    .order("starts_at", { ascending: true });
  return data ?? [];
}

export async function getClassById(id: string) {
  const supabase = createClient();
  const { data } = await supabase.from("classes").select("*").eq("id", id).single();
  return data;
}
