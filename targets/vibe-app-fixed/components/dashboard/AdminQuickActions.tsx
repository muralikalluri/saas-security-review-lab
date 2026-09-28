const rowStyle: React.CSSProperties = {
  border: "1px solid #ddd",
  borderRadius: "8px",
  padding: "16px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};

const ACTIONS = [
  {
    title: "Grant credits to a member",
    detail: "Use the form on /admin - posts to /api/admin/grant-credits (B-06, fixed: server-side role check).",
    tag: "See /admin",
  },
  {
    title: "Review member roster",
    detail: "Names only - see /studio/members (B-11, fixed: server selects only id/full_name).",
    tag: "See /studio/members",
  },
  {
    title: "Cancel a booking on a member's behalf",
    detail: "Not implemented from this dashboard - use the member's own /bookings page, or POST /api/bookings/[id]/cancel directly (B-05, fixed: ownership-checked).",
    tag: "Manual only",
  },
  {
    title: "Reconcile Stripe credit purchases",
    detail: "Handled by /api/stripe/webhook - signature-verified (B-07) and idempotent (B-08).",
    tag: "Automatic",
  },
];

export default function AdminQuickActions() {
  return (
    <section style={{ marginBottom: "32px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Admin quick actions</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {ACTIONS.map((action) => (
          <div key={action.title} style={rowStyle}>
            <div>
              <p style={{ margin: 0, fontWeight: 600 }}>{action.title}</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>{action.detail}</p>
            </div>
            <span style={{ fontSize: "12px", color: "#999" }}>{action.tag}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
