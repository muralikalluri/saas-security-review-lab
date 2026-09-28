import "server-only";
import { getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-06 (fixed, SPEC.md B-06): reads the caller's role from `profiles.role`
 * via the service-role client - never from `user_metadata` (writable by
 * the user themselves via `auth.updateUser`), the request body, or
 * unverified JWT claims. `getSessionUser()` already verifies the session
 * with the auth server before returning a user. Shared by every
 * admin-only route/page instead of each one re-implementing its own check.
 */
export async function requireAdmin() {
  const user = await getSessionUser();
  if (!user) {
    return { user: null, isAdmin: false as const };
  }
  const admin = createAdminClient();
  const { data: profile } = await admin.from("profiles").select("role").eq("id", user.id).single();
  return { user, isAdmin: profile?.role === "admin" };
}
