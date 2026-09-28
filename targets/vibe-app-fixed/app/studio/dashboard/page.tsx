import { createClient, getSessionUser } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-12 (seeded flaw, SPEC.md B-12): "Structure / maintainability" - this is
 * the ~600-line page file called out in SPEC.md's B-12 row. It has every
 * symptom listed there in one place:
 *   1. Supabase queries written inline, scattered across the page, instead
 *      of a shared data-access layer - four separate `createClient()`
 *      calls below, each firing its own query, instead of one data module
 *      the page (and the API routes) could both import.
 *   2. The credit-cost pricing formula is pasted a THIRD time
 *      (`dashboardEstimateCreditCost` below) - see lib/pricing.ts (the
 *      client display estimate, clamped) and app/api/bookings/route.ts
 *      (the server charge, not clamped). All three should be one function.
 *   3. No tests - this file has zero test coverage (see package.json's
 *      `vitest run` with no spec files yet; wired up for M6).
 *   4. It is a single ~600-line file mixing data fetching, aggregation and
 *      rendering, instead of being split into smaller components.
 * None of this is a security bug on its own - it is the maintainability
 * finding: a page this size, with this much duplicated logic and no
 * tests, is exactly the kind of surface where a fix for one bug (e.g. the
 * B-10 clamp) gets applied in one of the three pricing copies and silently
 * missed in the other two.
 */
export default async function StudioDashboardPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const supabaseRole = createClient();
  const { data: profile } = await supabaseRole.from("profiles").select("role").eq("id", user.id).single();
  if (profile?.role !== "admin") {
    return <main>You do not have access to this page.</main>;
  }

  // --- inline query #1: every upcoming/past class -------------------------
  const supabaseClasses = createClient();
  const { data: classes } = await supabaseClasses.from("classes").select("*").order("starts_at", { ascending: true });

  // --- inline query #2: every booking, confirmed or cancelled -------------
  // (fixed, B-03/B-04): reads via the service-role client - after enabling
  // RLS on bookings/profiles, a regular session client would only see the
  // admin's OWN rows. This page already re-verified the caller is an admin
  // above, so the elevated read here is intentional and gated.
  const supabaseBookings = createAdminClient();
  const { data: bookings } = await supabaseBookings.from("bookings").select("*");

  // --- inline query #3: every member profile -------------------------------
  const supabaseMembers = createAdminClient();
  const { data: members } = await supabaseMembers.from("profiles").select("*");

  // --- inline query #4: cancelled bookings, re-fetched separately instead
  // of filtered from query #2 above - a shared data layer would not do
  // the same round trip twice with slightly different filters.
  const supabaseCancellations = createAdminClient();
  const { data: cancellations } = await supabaseCancellations.from("bookings").select("*").eq("status", "cancelled");

  const allClasses = classes ?? [];
  const allBookings = bookings ?? [];
  const allMembers = members ?? [];
  const allCancellations = cancellations ?? [];

  // ---- duplicated pricing/credit-cost formula, THIRD COPY (B-12) ----------
  // Same shape as lib/pricing.ts's estimateCreditCost and the inline copy
  // in app/api/bookings/route.ts, pasted here a third time instead of
  // imported. Like the server copy (and unlike lib/pricing.ts) this one
  // has no Math.max(1, ...) clamp either - the dashboard would happily
  // show a negative "credits collected" figure for a B-10 booking.
  function dashboardEstimateCreditCost(creditCostPerSeat: number, quantity: number): number {
    return creditCostPerSeat * quantity;
  }

  const classById = new Map(allClasses.map((c: any) => [c.id, c]));
  const memberById = new Map(allMembers.map((m: any) => [m.id, m]));

  const confirmedBookings = allBookings.filter((b: any) => b.status === "confirmed");

  const seatsBookedByClass = new Map<string, number>();
  const revenueByClass = new Map<string, number>();
  const creditsByClass = new Map<string, number>();
  for (const booking of confirmedBookings) {
    const cls = classById.get(booking.class_id);
    if (!cls) continue;
    seatsBookedByClass.set(booking.class_id, (seatsBookedByClass.get(booking.class_id) ?? 0) + booking.quantity);
    revenueByClass.set(booking.class_id, (revenueByClass.get(booking.class_id) ?? 0) + booking.quantity * cls.price_cents);
    creditsByClass.set(
      booking.class_id,
      (creditsByClass.get(booking.class_id) ?? 0) + dashboardEstimateCreditCost(cls.credit_cost, booking.quantity)
    );
  }

  const revenueByStudio = new Map<string, number>();
  const bookingsByStudio = new Map<string, number>();
  for (const cls of allClasses) {
    const revenue = revenueByClass.get(cls.id) ?? 0;
    const seats = seatsBookedByClass.get(cls.id) ?? 0;
    revenueByStudio.set(cls.studio_name, (revenueByStudio.get(cls.studio_name) ?? 0) + revenue);
    bookingsByStudio.set(cls.studio_name, (bookingsByStudio.get(cls.studio_name) ?? 0) + seats);
  }

  const revenueByInstructor = new Map<string, number>();
  const classesByInstructor = new Map<string, number>();
  for (const cls of allClasses) {
    const revenue = revenueByClass.get(cls.id) ?? 0;
    revenueByInstructor.set(cls.instructor, (revenueByInstructor.get(cls.instructor) ?? 0) + revenue);
    classesByInstructor.set(cls.instructor, (classesByInstructor.get(cls.instructor) ?? 0) + 1);
  }

  const totalRevenueCents = Array.from(revenueByClass.values()).reduce((sum, n) => sum + n, 0);
  const totalCreditsCollected = Array.from(creditsByClass.values()).reduce((sum, n) => sum + n, 0);
  const totalSeatsBooked = confirmedBookings.reduce((sum: number, b: any) => sum + b.quantity, 0);
  const totalOutstandingCredits = allMembers.reduce((sum: number, m: any) => sum + m.credit_balance, 0);

  const lowCreditMembers = allMembers.filter((m: any) => m.credit_balance <= 2);

  const now = Date.now();
  const weekBuckets = [0, 1, 2, 3].map((weeksAgo) => {
    const end = now - weeksAgo * 7 * 24 * 60 * 60 * 1000;
    const start = end - 7 * 24 * 60 * 60 * 1000;
    const bookingsInWeek = allBookings.filter((b: any) => {
      const t = new Date(b.created_at).getTime();
      return t >= start && t < end;
    });
    const seats = bookingsInWeek.reduce((sum: number, b: any) => sum + b.quantity, 0);
    return { weeksAgo, seats, count: bookingsInWeek.length };
  });

  return (
    <main style={{ padding: "24px", fontFamily: "system-ui, -apple-system, sans-serif", color: "#1a1a1a" }}>
      <header style={{ marginBottom: "32px", borderBottom: "1px solid #e2e2e2", paddingBottom: "16px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, margin: 0 }}>Studio dashboard</h1>
        <p style={{ fontSize: "14px", color: "#666", marginTop: "4px" }}>
          StudioBook (fictional) - internal admin view, signed in as {user.email}
        </p>
      </header>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Today&apos;s snapshot</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "16px" }}>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Total classes
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{allClasses.length}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Confirmed bookings
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{confirmedBookings.length}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Seats booked
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{totalSeatsBooked}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Revenue (fictional)
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>${(totalRevenueCents / 100).toFixed(2)}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Credits collected
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{totalCreditsCollected}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Credits outstanding
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{totalOutstandingCredits}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Cancellations
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{allCancellations.length}</p>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "160px", flex: "1 1 160px" }}>
            <p style={{ fontSize: "12px", color: "#666", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Low-credit members
            </p>
            <p style={{ fontSize: "28px", fontWeight: 700, margin: "4px 0 0" }}>{lowCreditMembers.length}</p>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Upcoming classes</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Title</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Instructor</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Studio</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Seats</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Revenue</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Credits</th>
            </tr>
          </thead>
          <tbody>
            {allClasses.map((cls: any) => {
              const seats = seatsBookedByClass.get(cls.id) ?? 0;
              const revenue = revenueByClass.get(cls.id) ?? 0;
              const credits = creditsByClass.get(cls.id) ?? 0;
              return (
                <tr key={cls.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{cls.title}</td>
                  <td style={{ padding: "8px" }}>{cls.instructor}</td>
                  <td style={{ padding: "8px" }}>{cls.studio_name}</td>
                  <td style={{ padding: "8px" }}>
                    {seats} / {cls.capacity}
                  </td>
                  <td style={{ padding: "8px" }}>${(revenue / 100).toFixed(2)}</td>
                  <td style={{ padding: "8px" }}>{credits}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Member credit ledger</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Name</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Email</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Role</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Credit balance</th>
            </tr>
          </thead>
          <tbody>
            {allMembers.map((member: any) => {
              const isLow = member.credit_balance <= 2;
              return (
                <tr key={member.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{member.full_name}</td>
                  <td style={{ padding: "8px" }}>{member.email}</td>
                  <td style={{ padding: "8px" }}>{member.role}</td>
                  <td style={{ padding: "8px", color: isLow ? "#b45309" : "#1a1a1a", fontWeight: isLow ? 700 : 400 }}>
                    {member.credit_balance}
                    {isLow ? " (low)" : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Recent bookings</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Member</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Class</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Quantity</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Status</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {allBookings.map((booking: any) => {
              const member = memberById.get(booking.user_id);
              const cls = classById.get(booking.class_id);
              return (
                <tr key={booking.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{member?.full_name ?? "unknown"}</td>
                  <td style={{ padding: "8px" }}>{cls?.title ?? "unknown"}</td>
                  <td style={{ padding: "8px" }}>{booking.quantity}</td>
                  <td style={{ padding: "8px" }}>{booking.status}</td>
                  <td style={{ padding: "8px" }}>{new Date(booking.created_at).toLocaleDateString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Cancellations</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Member</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Class</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Quantity</th>
            </tr>
          </thead>
          <tbody>
            {allCancellations.map((booking: any) => {
              const member = memberById.get(booking.user_id);
              const cls = classById.get(booking.class_id);
              return (
                <tr key={booking.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{member?.full_name ?? "unknown"}</td>
                  <td style={{ padding: "8px" }}>{cls?.title ?? "unknown"}</td>
                  <td style={{ padding: "8px" }}>{booking.quantity}</td>
                </tr>
              );
            })}
            {allCancellations.length === 0 ? (
              <tr>
                <td style={{ padding: "8px" }} colSpan={3}>
                  No cancellations yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Revenue by studio location</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Studio</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Seats booked</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {Array.from(revenueByStudio.entries()).map(([studioName, revenue]) => (
              <tr key={studioName} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>{studioName}</td>
                <td style={{ padding: "8px" }}>{bookingsByStudio.get(studioName) ?? 0}</td>
                <td style={{ padding: "8px" }}>${(revenue / 100).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Instructor roster</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Instructor</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Classes</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {Array.from(classesByInstructor.entries()).map(([instructor, count]) => (
              <tr key={instructor} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>{instructor}</td>
                <td style={{ padding: "8px" }}>{count}</td>
                <td style={{ padding: "8px" }}>${((revenueByInstructor.get(instructor) ?? 0) / 100).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Bookings, last 4 weeks</h2>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
          {weekBuckets[0] ? (
            <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "140px", flex: "1 1 140px" }}>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>This week</p>
              <p style={{ fontSize: "22px", fontWeight: 700, margin: "4px 0 0" }}>{weekBuckets[0].seats} seats</p>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{weekBuckets[0].count} bookings</p>
            </div>
          ) : null}
          {weekBuckets[1] ? (
            <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "140px", flex: "1 1 140px" }}>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>1 week ago</p>
              <p style={{ fontSize: "22px", fontWeight: 700, margin: "4px 0 0" }}>{weekBuckets[1].seats} seats</p>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{weekBuckets[1].count} bookings</p>
            </div>
          ) : null}
          {weekBuckets[2] ? (
            <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "140px", flex: "1 1 140px" }}>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>2 weeks ago</p>
              <p style={{ fontSize: "22px", fontWeight: 700, margin: "4px 0 0" }}>{weekBuckets[2].seats} seats</p>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{weekBuckets[2].count} bookings</p>
            </div>
          ) : null}
          {weekBuckets[3] ? (
            <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", minWidth: "140px", flex: "1 1 140px" }}>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>3 weeks ago</p>
              <p style={{ fontSize: "22px", fontWeight: 700, margin: "4px 0 0" }}>{weekBuckets[3].seats} seats</p>
              <p style={{ fontSize: "12px", color: "#666", margin: 0 }}>{weekBuckets[3].count} bookings</p>
            </div>
          ) : null}
        </div>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Low-credit members (2 or fewer)</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Name</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Email</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Credit balance</th>
            </tr>
          </thead>
          <tbody>
            {lowCreditMembers.map((member: any) => (
              <tr key={member.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>{member.full_name}</td>
                <td style={{ padding: "8px" }}>{member.email}</td>
                <td style={{ padding: "8px", color: "#b45309", fontWeight: 700 }}>{member.credit_balance}</td>
              </tr>
            ))}
            {lowCreditMembers.length === 0 ? (
              <tr>
                <td style={{ padding: "8px" }} colSpan={3}>
                  No members below the threshold.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Class capacity utilization</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Class</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Booked</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Capacity</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Utilization</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {allClasses.map((cls: any) => {
              const seats = seatsBookedByClass.get(cls.id) ?? 0;
              const utilization = cls.capacity > 0 ? Math.round((seats / cls.capacity) * 100) : 0;
              let statusLabel = "Open";
              let statusColor = "#166534";
              if (utilization >= 100) {
                statusLabel = "Full";
                statusColor = "#991b1b";
              } else if (utilization >= 75) {
                statusLabel = "Filling up";
                statusColor = "#b45309";
              }
              return (
                <tr key={cls.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{cls.title}</td>
                  <td style={{ padding: "8px" }}>{seats}</td>
                  <td style={{ padding: "8px" }}>{cls.capacity}</td>
                  <td style={{ padding: "8px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div style={{ width: "100px", height: "8px", background: "#eee", borderRadius: "4px", overflow: "hidden" }}>
                        <div
                          style={{
                            width: `${Math.min(100, utilization)}%`,
                            height: "100%",
                            background: statusColor,
                          }}
                        />
                      </div>
                      <span style={{ fontSize: "12px", color: "#666" }}>{utilization}%</span>
                    </div>
                  </td>
                  <td style={{ padding: "8px", color: statusColor, fontWeight: 600 }}>{statusLabel}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Member signups</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Name</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Email</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Role</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Signed up</th>
            </tr>
          </thead>
          <tbody>
            {[...allMembers]
              .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .map((member: any) => (
                <tr key={member.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{member.full_name}</td>
                  <td style={{ padding: "8px" }}>{member.email}</td>
                  <td style={{ padding: "8px" }}>{member.role}</td>
                  <td style={{ padding: "8px" }}>{new Date(member.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Instructor breakdown by class</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
              <th style={{ padding: "8px", fontWeight: 600 }}>Instructor</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Class</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Studio</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Starts</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Seats booked</th>
              <th style={{ padding: "8px", fontWeight: 600 }}>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {[...allClasses]
              .sort((a: any, b: any) => a.instructor.localeCompare(b.instructor))
              .map((cls: any) => (
                <tr key={cls.id} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "8px" }}>{cls.instructor}</td>
                  <td style={{ padding: "8px" }}>{cls.title}</td>
                  <td style={{ padding: "8px" }}>{cls.studio_name}</td>
                  <td style={{ padding: "8px" }}>{new Date(cls.starts_at).toLocaleDateString()}</td>
                  <td style={{ padding: "8px" }}>{seatsBookedByClass.get(cls.id) ?? 0}</td>
                  <td style={{ padding: "8px" }}>${((revenueByClass.get(cls.id) ?? 0) / 100).toFixed(2)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Admin quick actions</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p style={{ margin: 0, fontWeight: 600 }}>Grant credits to a member</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>
                Use the form on /admin - posts to /api/admin/grant-credits (see B-06).
              </p>
            </div>
            <span style={{ fontSize: "12px", color: "#999" }}>See /admin</span>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p style={{ margin: 0, fontWeight: 600 }}>Review member roster</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>Full contact details for every member - see /studio/members (B-11).</p>
            </div>
            <span style={{ fontSize: "12px", color: "#999" }}>See /studio/members</span>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p style={{ margin: 0, fontWeight: 600 }}>Cancel a booking on a member&apos;s behalf</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>
                Not implemented from this dashboard yet - use the member&apos;s own /bookings page, or
                DELETE /api/bookings/[id]/cancel directly (see B-05).
              </p>
            </div>
            <span style={{ fontSize: "12px", color: "#999" }}>Manual only</span>
          </div>
          <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p style={{ margin: 0, fontWeight: 600 }}>Reconcile Stripe credit purchases</p>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>
                Handled by the webhook at /api/stripe/webhook - no signature check yet (B-07), no
                idempotency yet (B-08).
              </p>
            </div>
            <span style={{ fontSize: "12px", color: "#999" }}>Automatic</span>
          </div>
        </div>
      </section>

      <section style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "12px" }}>Data freshness</h2>
        <p style={{ fontSize: "13px", color: "#666" }}>
          This page fires four independent Supabase queries on every load (classes, bookings, members,
          cancellations) rather than one shared fetch, so the figures above can very briefly disagree
          with each other under concurrent writes - another consequence of the B-12 "no shared
          data-access layer" finding at the top of this file.
        </p>
      </section>

      <footer style={{ fontSize: "12px", color: "#999", borderTop: "1px solid #e2e2e2", paddingTop: "16px" }}>
        StudioBook admin dashboard (fictional). Every figure above is computed from four separate
        inline Supabase queries fired by this single page component - see the B-12 comment at the
        top of this file.
      </footer>
    </main>
  );
}
