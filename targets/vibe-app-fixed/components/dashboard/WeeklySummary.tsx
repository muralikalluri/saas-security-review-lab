const cardStyle: React.CSSProperties = { border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "140px", flex: "1 1 140px" };
const LABELS = ["This week", "1 week ago", "2 weeks ago", "3 weeks ago"];

export default function WeeklySummary({ weekBuckets }: { weekBuckets: { weeksAgo: number; seats: number; count: number }[] }) {
  return (
    <section style={{ marginBottom: "32px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Bookings, last 4 weeks</h2>
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
        {weekBuckets.map((bucket) => (
          <div key={bucket.weeksAgo} style={cardStyle}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{LABELS[bucket.weeksAgo]}</p>
            <p style={{ fontSize: "22px", fontWeight: 700, margin: "4px 0 0" }}>{bucket.seats} seats</p>
            <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{bucket.count} bookings</p>
          </div>
        ))}
      </div>
    </section>
  );
}
