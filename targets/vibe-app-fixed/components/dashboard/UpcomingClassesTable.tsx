import * as s from "./tableStyles";

export default function UpcomingClassesTable({
  classes,
  seatsBookedByClass,
  revenueByClass,
  creditsByClass,
}: {
  classes: any[];
  seatsBookedByClass: Map<string, number>;
  revenueByClass: Map<string, number>;
  creditsByClass: Map<string, number>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Upcoming classes</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Title</th>
            <th style={s.th}>Instructor</th>
            <th style={s.th}>Studio</th>
            <th style={s.th}>Seats</th>
            <th style={s.th}>Revenue</th>
            <th style={s.th}>Credits</th>
          </tr>
        </thead>
        <tbody>
          {classes.map((cls) => {
            const seats = seatsBookedByClass.get(cls.id) ?? 0;
            const revenue = revenueByClass.get(cls.id) ?? 0;
            const credits = creditsByClass.get(cls.id) ?? 0;
            return (
              <tr key={cls.id} style={s.bodyRow}>
                <td style={s.td}>{cls.title}</td>
                <td style={s.td}>{cls.instructor}</td>
                <td style={s.td}>{cls.studio_name}</td>
                <td style={s.td}>
                  {seats} / {cls.capacity}
                </td>
                <td style={s.td}>${(revenue / 100).toFixed(2)}</td>
                <td style={s.td}>{credits}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
