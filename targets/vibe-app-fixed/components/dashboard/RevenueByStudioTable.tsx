import * as s from "./tableStyles";

export default function RevenueByStudioTable({
  revenueByStudio,
  bookingsByStudio,
}: {
  revenueByStudio: Map<string, number>;
  bookingsByStudio: Map<string, number>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Revenue by studio location</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Studio</th>
            <th style={s.th}>Seats booked</th>
            <th style={s.th}>Revenue</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(revenueByStudio.entries()).map(([studioName, revenue]) => (
            <tr key={studioName} style={s.bodyRow}>
              <td style={s.td}>{studioName}</td>
              <td style={s.td}>{bookingsByStudio.get(studioName) ?? 0}</td>
              <td style={s.td}>${(revenue / 100).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
