import { requireAdmin } from "@/lib/auth/require-admin";
import AdminUserList from "@/components/AdminUserList";
import GrantCreditsForm from "@/components/GrantCreditsForm";

/**
 * B-06 (fixed, SPEC.md B-06): this page's own check is still UI-only (it
 * just decides what to render) - what actually matters is that
 * POST /api/admin/grant-credits and GET /api/admin/users independently
 * re-check the caller's role server-side via the same requireAdmin()
 * helper, so calling those routes directly (bypassing this page entirely)
 * is no longer sufficient to use them.
 */
export default async function AdminPage() {
  const { user, isAdmin } = await requireAdmin();
  if (!user) {
    return <main>Please sign in.</main>;
  }
  if (!isAdmin) {
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
