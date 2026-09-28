import Link from "next/link";
import { getSessionUser } from "@/lib/supabase/server";
import { listUpcomingClasses } from "@/lib/data/classes";

export default async function HomePage() {
  const user = await getSessionUser();
  const classes = await listUpcomingClasses();

  return (
    <main>
      <h1>StudioBook (fictional)</h1>
      {!user && (
        <p>
          <Link href="/login">Sign in</Link> to book a class.
        </p>
      )}
      {user && (
        <p>
          Signed in. <Link href="/bookings">My bookings</Link> · <Link href="/profile">Profile</Link> ·{" "}
          <Link href="/admin">Admin</Link>
        </p>
      )}
      <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "0.75rem" }}>
        {classes.map((c) => (
          <li key={c.id} style={{ border: "1px solid #ddd", borderRadius: 6, padding: "0.75rem" }}>
            <strong>{c.title}</strong> with {c.instructor} - {c.studio_name}
            <br />
            {new Date(c.starts_at).toLocaleString()} - {c.credit_cost} credit(s) (${(c.price_cents / 100).toFixed(2)})
            <br />
            <Link href={`/classes/${c.id}`}>View &amp; book</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
