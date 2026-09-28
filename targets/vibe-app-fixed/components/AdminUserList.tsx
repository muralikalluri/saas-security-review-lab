"use client";

import { useEffect, useState } from "react";

/**
 * B-01 (fixed, SPEC.md B-01): fetches from the server-side /api/admin/users
 * route instead of building a Supabase client with the service-role key
 * directly in this "use client" component. No service-role key, prefixed
 * or otherwise, exists anywhere in client-reachable code.
 */
export default function AdminUserList() {
  const [users, setUsers] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/admin/users")
      .then((r) => r.json())
      .then(({ users }) => setUsers(users ?? []));
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
