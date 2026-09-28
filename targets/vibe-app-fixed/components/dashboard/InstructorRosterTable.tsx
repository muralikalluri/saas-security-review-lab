import * as s from "./tableStyles";

export default function InstructorRosterTable({
  classesByInstructor,
  revenueByInstructor,
}: {
  classesByInstructor: Map<string, number>;
  revenueByInstructor: Map<string, number>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Instructor roster</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Instructor</th>
            <th style={s.th}>Classes</th>
            <th style={s.th}>Revenue</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(classesByInstructor.entries()).map(([instructor, count]) => (
            <tr key={instructor} style={s.bodyRow}>
              <td style={s.td}>{instructor}</td>
              <td style={s.td}>{count}</td>
              <td style={s.td}>${((revenueByInstructor.get(instructor) ?? 0) / 100).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
