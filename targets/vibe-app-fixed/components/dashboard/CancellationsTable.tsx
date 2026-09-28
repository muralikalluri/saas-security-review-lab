import * as s from "./tableStyles";

export default function CancellationsTable({
  cancellations,
  memberById,
  classById,
}: {
  cancellations: any[];
  memberById: Map<string, any>;
  classById: Map<string, any>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Cancellations</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Member</th>
            <th style={s.th}>Class</th>
            <th style={s.th}>Quantity</th>
          </tr>
        </thead>
        <tbody>
          {cancellations.map((booking) => {
            const member = memberById.get(booking.user_id);
            const cls = classById.get(booking.class_id);
            return (
              <tr key={booking.id} style={s.bodyRow}>
                <td style={s.td}>{member?.full_name ?? "unknown"}</td>
                <td style={s.td}>{cls?.title ?? "unknown"}</td>
                <td style={s.td}>{booking.quantity}</td>
              </tr>
            );
          })}
          {cancellations.length === 0 ? (
            <tr>
              <td style={s.td} colSpan={3}>
                No cancellations yet.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}
