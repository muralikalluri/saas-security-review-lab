import { createClient, getSessionUser } from "@/lib/supabase/server";
import AdminUserList from "@/components/AdminUserList";
import GrantCreditsForm from "@/components/GrantCreditsForm";

/**
 * B-06 (seeded flaw, SPEC.md B-06): this page hides the admin tools behind
 * a role check - but that check is UI-only. The server action it renders
 * a form for (POST /api/admin/grant-credits) does not re-check the role
 * itself, so any authenticated user who calls that route directly (not
 * through this page) can use it regardless of what's rendered here.
 */
export default async function AdminPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const supabase = createClient();
  const { data: profile } = await supabase.from("profiles").select("role").eq("id", user.id).single();

  if (profile?.role !== "admin") {
    return <main>You do not have access to this page.</main>;
  }

  return (
    <main>
      <h1>Admin</h1>
      <h2>All users</h2>
      <AdminUserList />
      <h2>Grant credits</h2>
      <GrantCreditsForm />
    </main>
  );
}
