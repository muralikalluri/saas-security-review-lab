import "server-only";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * Service-role client. SERVER ONLY - the `server-only` import above makes
 * Next.js fail the build if any client component ever imports this file.
 * B-01 (fixed, SPEC.md B-01): components/AdminUserList.tsx no longer builds
 * its own service-role client from a NEXT_PUBLIC_-prefixed var in a "use
 * client" component - it fetches from app/api/admin/users/route.ts, which
 * uses this file correctly instead.
 */
export function createAdminClient() {
  return createSupabaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } }
  );
}
