import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { getSessionUser } from "@/lib/supabase/server";

// B-12 (seeded flaw, SPEC.md B-12): this Supabase query is written inline
// in the page component instead of a shared data-access module - the same
// pattern repeats in app/bookings/page.tsx, app/admin/page.tsx, and the
// API routes, each with its own slightly different way of talking to the
// `classes`/`bookings` tables. A real fix (M6) would centralise this.
export default async function HomePage() {
  const user = await getSessionUser();
  const supabase = createClient();
  const { data: classes } = await supabase
    .from("classes")
    .select("id, title, instructor, studio_name, capacity, price_cents, credit_cost, starts_at")
    .order("starts_at", { ascending: true });

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
        {(classes ?? []).map((c) => (
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
