import { createClient, getSessionUser } from "@/lib/supabase/server";
import CancelButton from "@/components/CancelButton";

export default async function BookingsPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const supabase = createClient();
  const { data: bookings } = await supabase
    .from("bookings")
    .select("id, quantity, status, classes(title, starts_at)")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  return (
    <main>
      <h1>My bookings</h1>
      <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "0.5rem" }}>
        {(bookings ?? []).map((b: any) => (
          <li key={b.id} style={{ border: "1px solid #ddd", borderRadius: 6, padding: "0.5rem" }}>
            {b.classes?.title} - {b.quantity} seat(s) - {b.status}
            {b.status === "confirmed" && <CancelButton bookingId={b.id} />}
          </li>
        ))}
      </ul>
    </main>
  );
}
