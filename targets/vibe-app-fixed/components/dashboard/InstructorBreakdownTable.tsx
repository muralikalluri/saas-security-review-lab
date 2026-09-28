import * as s from "./tableStyles";

export default function InstructorBreakdownTable({
  classes,
  seatsBookedByClass,
  revenueByClass,
}: {
  classes: any[];
  seatsBookedByClass: Map<string, number>;
  revenueByClass: Map<string, number>;
}) {
  const sorted = [...classes].sort((a, b) => a.instructor.localeCompare(b.instructor));
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Instructor breakdown by class</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Instructor</th>
            <th style={s.th}>Class</th>
            <th style={s.th}>Studio</th>
            <th style={s.th}>Starts</th>
            <th style={s.th}>Seats booked</th>
            <th style={s.th}>Revenue</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((cls) => (
            <tr key={cls.id} style={s.bodyRow}>
              <td style={s.td}>{cls.instructor}</td>
              <td style={s.td}>{cls.title}</td>
              <td style={s.td}>{cls.studio_name}</td>
              <td style={s.td}>{new Date(cls.starts_at).toLocaleDateString()}</td>
              <td style={s.td}>{seatsBookedByClass.get(cls.id) ?? 0}</td>
              <td style={s.td}>${((revenueByClass.get(cls.id) ?? 0) / 100).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
