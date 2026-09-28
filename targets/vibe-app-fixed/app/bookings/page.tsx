import { getSessionUser } from "@/lib/supabase/server";
import { listMyBookings } from "@/lib/data/bookings";
import CancelButton from "@/components/CancelButton";

export default async function BookingsPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const bookings = await listMyBookings(user.id);

  return (
    <main>
      <h1>My bookings</h1>
      <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "0.5rem" }}>
        {bookings.map((b: any) => (
          <li key={b.id} style={{ border: "1px solid #ddd", borderRadius: 6, padding: "0.5rem" }}>
            {b.classes?.title} - {b.quantity} seat(s) - {b.status}
            {b.status === "confirmed" && <CancelButton bookingId={b.id} />}
          </li>
        ))}
      </ul>
    </main>
  );
}
