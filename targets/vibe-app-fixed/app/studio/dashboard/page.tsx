import { requireAdmin } from "@/lib/auth/require-admin";
import { loadDashboardData } from "@/lib/data/dashboard";
import StatsGrid from "@/components/dashboard/StatsGrid";
import UpcomingClassesTable from "@/components/dashboard/UpcomingClassesTable";
import MemberLedgerTable from "@/components/dashboard/MemberLedgerTable";
import RecentBookingsTable from "@/components/dashboard/RecentBookingsTable";
import CancellationsTable from "@/components/dashboard/CancellationsTable";
import RevenueByStudioTable from "@/components/dashboard/RevenueByStudioTable";
import InstructorRosterTable from "@/components/dashboard/InstructorRosterTable";
import WeeklySummary from "@/components/dashboard/WeeklySummary";
import LowCreditMembersTable from "@/components/dashboard/LowCreditMembersTable";
import CapacityUtilizationTable from "@/components/dashboard/CapacityUtilizationTable";
import MemberSignupsTable from "@/components/dashboard/MemberSignupsTable";
import InstructorBreakdownTable from "@/components/dashboard/InstructorBreakdownTable";
import AdminQuickActions from "@/components/dashboard/AdminQuickActions";
import DataFreshnessNote from "@/components/dashboard/DataFreshnessNote";

/**
 * B-12 (fixed, SPEC.md B-12): this page used to be the ~600-line file
 * SPEC.md's B-12 row describes - inline queries, a third duplicated
 * pricing formula, no tests, everything in one file. Now: data fetching +
 * aggregation live in lib/data/dashboard.ts (one shared module), the
 * pricing formula comes from lib/pricing.ts (see app/api/bookings/route.ts
 * for the other caller), and rendering is split across
 * components/dashboard/*. This file is just the admin check + wiring data
 * to components. Tests: lib/pricing.test.ts covers the validating formula.
 */
export default async function StudioDashboardPage() {
  const { user, isAdmin } = await requireAdmin();
  if (!user) {
    return <main>Please sign in.</main>;
  }
  if (!isAdmin) {
    return <main>You do not have access to this page.</main>;
  }

  const data = await loadDashboardData();

  return (
    <main style={{ padding: "24px", fontFamily: "system-ui, -apple-system, sans-serif", color: "#1a1a1a" }}>
      <header style={{ marginBottom: "32px", borderBottom: "1px solid #e2e2e2", paddingBottom: "16px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700, margin: 0 }}>Studio dashboard</h1>
        <p style={{ fontSize: "14px", color: "#666", marginTop: "4px" }}>
          StudioBook (fictional) - internal admin view, signed in as {user.email}
        </p>
      </header>

      <StatsGrid
        totalClasses={data.allClasses.length}
        confirmedBookings={data.confirmedBookings.length}
        totalSeatsBooked={data.totalSeatsBooked}
        totalRevenueCents={data.totalRevenueCents}
        totalCreditsCollected={data.totalCreditsCollected}
        totalOutstandingCredits={data.totalOutstandingCredits}
        cancellations={data.allCancellations.length}
        lowCreditMembers={data.lowCreditMembers.length}
      />
      <UpcomingClassesTable
        classes={data.allClasses}
        seatsBookedByClass={data.seatsBookedByClass}
        revenueByClass={data.revenueByClass}
        creditsByClass={data.creditsByClass}
      />
      <MemberLedgerTable members={data.allMembers} />
      <RecentBookingsTable bookings={data.allBookings} memberById={data.memberById} classById={data.classById} />
      <CancellationsTable cancellations={data.allCancellations} memberById={data.memberById} classById={data.classById} />
      <RevenueByStudioTable revenueByStudio={data.revenueByStudio} bookingsByStudio={data.bookingsByStudio} />
      <InstructorRosterTable classesByInstructor={data.classesByInstructor} revenueByInstructor={data.revenueByInstructor} />
      <WeeklySummary weekBuckets={data.weekBuckets} />
      <LowCreditMembersTable members={data.lowCreditMembers} />
      <CapacityUtilizationTable classes={data.allClasses} seatsBookedByClass={data.seatsBookedByClass} />
      <MemberSignupsTable members={data.allMembers} />
      <InstructorBreakdownTable classes={data.allClasses} seatsBookedByClass={data.seatsBookedByClass} revenueByClass={data.revenueByClass} />
      <AdminQuickActions />
      <DataFreshnessNote />

      <footer style={{ fontSize: "12px", color: "#999", borderTop: "1px solid #e2e2e2", paddingTop: "16px" }}>
        StudioBook admin dashboard (fictional). Data fetching lives in lib/data/dashboard.ts, not in this
        component - see the B-12 comment above.
      </footer>
    </main>
  );
}
