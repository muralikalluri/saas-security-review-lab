"use client";

import { useEffect, useState } from "react";
import { createClient as createSupabaseClient } from "@supabase/supabase-js";

/**
 * B-01 (seeded flaw, SPEC.md B-01): a "quick and easy" way to list every
 * user for the admin dashboard - built by constructing a Supabase client
 * with the SERVICE ROLE key directly in this "use client" component, read
 * from a `NEXT_PUBLIC_`-prefixed env var. Next.js inlines every
 * `NEXT_PUBLIC_*` variable into the browser bundle at build time, so the
 * service-role key - which bypasses every RLS policy in the database -
 * ships to every visitor's browser, not just admins. Contrast with
 * lib/supabase/admin.ts, which does this correctly (server-only, real
 * env var) but is simply not used here.
 */
const supabaseAdminInBrowser = createSupabaseClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!
);

export default function AdminUserList() {
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => {
    supabaseAdminInBrowser
      .from("profiles")
      .select("*")
      .then(({ data }) => setUsers(data ?? []));
  }, []);

  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Phone</th>
          <th>Role</th>
          <th>Credits</th>
          <th>User id</th>
        </tr>
      </thead>
      <tbody>
        {users.map((u) => (
          <tr key={u.id}>
            <td>{u.full_name}</td>
            <td>{u.email}</td>
            <td>{u.phone}</td>
            <td>{u.role}</td>
            <td>{u.credit_balance}</td>
            <td>
              <code>{u.id}</code>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
