import * as s from "./tableStyles";

function utilizationStatus(utilization: number): { label: string; color: string } {
  if (utilization >= 100) return { label: "Full", color: "#991b1b" };
  if (utilization >= 75) return { label: "Filling up", color: "#b45309" };
  return { label: "Open", color: "#166534" };
}

export default function CapacityUtilizationTable({
  classes,
  seatsBookedByClass,
}: {
  classes: any[];
  seatsBookedByClass: Map<string, number>;
}) {
  return (
    <section style={s.section}>
      <h2 style={s.sectionTitle}>Class capacity utilization</h2>
      <table style={s.table}>
        <thead>
          <tr style={s.headRow}>
            <th style={s.th}>Class</th>
            <th style={s.th}>Booked</th>
            <th style={s.th}>Capacity</th>
            <th style={s.th}>Utilization</th>
            <th style={s.th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {classes.map((cls) => {
            const seats = seatsBookedByClass.get(cls.id) ?? 0;
            const utilization = cls.capacity > 0 ? Math.round((seats / cls.capacity) * 100) : 0;
            const status = utilizationStatus(utilization);
            return (
              <tr key={cls.id} style={s.bodyRow}>
                <td style={s.td}>{cls.title}</td>
                <td style={s.td}>{seats}</td>
                <td style={s.td}>{cls.capacity}</td>
                <td style={s.td}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ width: "100px", height: "8px", background: "#eee", borderRadius: "4px", overflow: "hidden" }}>
                      <div style={{ width: `${Math.min(100, utilization)}%`, height: "100%", background: status.color }} />
                    </div>
                    <span style={{ fontSize: "12px", color: "#666" }}>{utilization}%</span>
                  </div>
                </td>
                <td style={{ ...s.td, color: status.color, fontWeight: 600 }}>{status.label}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
