import "server-only";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * Service-role client. SERVER ONLY - the `server-only` import above makes
 * Next.js fail the build if any client component ever imports this file.
 * Contrast with components/AdminUserList.tsx (B-01), which does NOT use
 * this file and instead builds its own service-role client directly in a
 * "use client" component, from a NEXT_PUBLIC_-prefixed env var - shipping
 * the key to the browser bundle regardless of this file existing correctly.
 */
export function createAdminClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  );
}
