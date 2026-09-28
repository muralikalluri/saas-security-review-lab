export default function DataFreshnessNote() {
  return (
    <section style={{ marginBottom: "32px" }}>
      <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Data freshness</h2>
      <p style={{ fontSize: "13px", color: "#666" }}>
        lib/data/dashboard.ts fires its four Supabase queries in parallel (Promise.all) from one shared
        module - fixed from the baseline's four separate inline `createClient()` calls scattered across
        the page component (B-12). The figures above can still very briefly disagree with each other
        under concurrent writes, since they're independent reads, not one transaction.
      </p>
    </section>
  );
}
