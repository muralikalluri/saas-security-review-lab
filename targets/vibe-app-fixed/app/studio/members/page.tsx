import { getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import MemberNameList from "@/components/MemberNameList";

/**
 * B-11 (fixed, SPEC.md B-11): selects only {id, full_name} - the exact two
 * fields the page renders - instead of `select("*")`. Even if a future
 * change renders more of the row, there is no PII in the fetched payload to
 * leak in the first place; that's a stronger fix than trusting every
 * caller to keep filtering it out in JSX.
 *
 * Reads via the service-role client: this directory is meant to be visible
 * to any signed-in member (not just admins - see the auth-only check
 * below), and after B-04's fix a member's own RLS grant only covers their
 * own profile row. B-01's guardrail (server-only, never a client
 * component) still applies here.
 */
export default async function StudioMembersPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const admin = createAdminClient();
  const { data: members } = await admin.from("profiles").select("id, full_name").neq("id", user.id);

  return (
    <main>
      <h1>Studio members</h1>
      <MemberNameList members={members ?? []} />
    </main>
  );
}
