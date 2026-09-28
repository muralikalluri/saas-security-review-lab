import "server-only";
import { createAdminClient } from "@/lib/supabase/admin";
import { calculateCreditCost } from "@/lib/pricing";

/**
 * B-12 (fixed, SPEC.md B-12): ONE data-access module for the dashboard,
 * instead of four inline `createClient()` calls scattered across the page
 * component. Reads via the service-role client: this is an admin-only page
 * (the caller is re-verified with requireAdmin() before this is ever
 * called), and after B-03/B-04's RLS fix a normal session client would
 * only see the admin's own rows.
 */
export async function loadDashboardData() {
  const admin = createAdminClient();

  const [{ data: classes }, { data: bookings }, { data: members }, { data: cancellations }] = await Promise.all([
    admin.from("classes").select("*").order("starts_at", { ascending: true }),
    admin.from("bookings").select("*"),
    admin.from("profiles").select("*"),
    admin.from("bookings").select("*").eq("status", "cancelled"),
  ]);

  const allClasses = classes ?? [];
  const allBookings = bookings ?? [];
  const allMembers = members ?? [];
  const allCancellations = cancellations ?? [];

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
    // B-12 (fixed): the credit-cost formula comes from lib/pricing.ts - the
    // baseline pasted a third, unclamped copy of this right here.
    creditsByClass.set(
      booking.class_id,
      (creditsByClass.get(booking.class_id) ?? 0) + calculateCreditCost(cls.credit_cost, booking.quantity)
    );
  }

  const revenueByStudio = new Map<string, number>();
  const bookingsByStudio = new Map<string, number>();
  const revenueByInstructor = new Map<string, number>();
  const classesByInstructor = new Map<string, number>();
  for (const cls of allClasses) {
    const revenue = revenueByClass.get(cls.id) ?? 0;
    const seats = seatsBookedByClass.get(cls.id) ?? 0;
    revenueByStudio.set(cls.studio_name, (revenueByStudio.get(cls.studio_name) ?? 0) + revenue);
    bookingsByStudio.set(cls.studio_name, (bookingsByStudio.get(cls.studio_name) ?? 0) + seats);
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
    return { weeksAgo, seats: bookingsInWeek.reduce((sum: number, b: any) => sum + b.quantity, 0), count: bookingsInWeek.length };
  });

  return {
    allClasses,
    allBookings,
    allMembers,
    allCancellations,
    classById,
    memberById,
    confirmedBookings,
    seatsBookedByClass,
    revenueByClass,
    creditsByClass,
    revenueByStudio,
    bookingsByStudio,
    revenueByInstructor,
    classesByInstructor,
    totalRevenueCents,
    totalCreditsCollected,
    totalSeatsBooked,
    totalOutstandingCredits,
    lowCreditMembers,
    weekBuckets,
  };
}

export type DashboardData = Awaited<ReturnType<typeof loadDashboardData>>;
