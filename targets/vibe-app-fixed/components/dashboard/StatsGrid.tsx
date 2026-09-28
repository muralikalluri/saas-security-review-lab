const cardStyle: React.CSSProperties = { border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" };
const labelStyle: React.CSSProperties = { fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" };
const valueStyle: React.CSSProperties = { fontSize: "28px", fontWeight: 700, margin: "4px 0 0" };

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={cardStyle}>
      <p style={labelStyle}>{label}</p>
      <p style={valueStyle}>{value}</p>
    </div>
  );
}

export default function StatsGrid(props: {
  totalClasses: number;
  confirmedBookings: number;
  totalSeatsBooked: number;
  totalRevenueCents: number;
  totalCreditsCollected: number;
  totalOutstandingCredits: number;
  cancellations: number;
  lowCreditMembers: number;
}) {
  return (
    <section style={{ marginBottom: "32px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Today&apos;s snapshot</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "16px" }}>
        <StatCard label="Total classes" value={props.totalClasses} />
        <StatCard label="Confirmed bookings" value={props.confirmedBookings} />
        <StatCard label="Seats booked" value={props.totalSeatsBooked} />
        <StatCard label="Revenue (fictional)" value={`$${(props.totalRevenueCents / 100).toFixed(2)}`} />
        <StatCard label="Credits collected" value={props.totalCreditsCollected} />
        <StatCard label="Credits outstanding" value={props.totalOutstandingCredits} />
        <StatCard label="Cancellations" value={props.cancellations} />
        <StatCard label="Low-credit members" value={props.lowCreditMembers} />
      </div>
    </section>
  );
}
