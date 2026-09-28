import * as s from "./tableStyles";

export default function RecentBookingsTable({
  bookings,
  memberById,
  classById,
}: {
  bookings: any[];
  memberById: Map<string, any>;
  classById: Map<string, any>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Recent bookings</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Member</th>
            <th style={s.th}>Class</th>
            <th style={s.th}>Quantity</th>
            <th style={s.th}>Status</th>
            <th style={s.th}>Created</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((booking) => {
            const member = memberById.get(booking.user_id);
            const cls = classById.get(booking.class_id);
            return (
              <tr key={booking.id} style={s.bodyRow}>
                <td style={s.td}>{member?.full_name ?? "unknown"}</td>
                <td style={s.td}>{cls?.title ?? "unknown"}</td>
                <td style={s.td}>{booking.quantity}</td>
                <td style={s.td}>{booking.status}</td>
                <td style={s.td}>{new Date(booking.created_at).toLocaleDateString()}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
