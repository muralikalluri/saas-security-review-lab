// B-12 (seeded flaw, SPEC.md B-12): this "display estimate" formula is
// duplicated, not shared, with the actual charge calculation in
// app/api/bookings/route.ts - nothing enforces they stay in sync, and
// they don't: this one clamps quantity to at least 1 for display, but the
// server-side copy has no such clamp (see B-10). A real fix (M6) would
// have both sides import ONE function from here.
export function estimateCreditCost(creditCostPerSeat: number, quantity: number): number {
  const displayQuantity = Math.max(1, quantity);
  return creditCostPerSeat * displayQuantity;
}
