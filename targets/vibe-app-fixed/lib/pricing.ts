/**
 * B-12 (fixed, SPEC.md B-12): the ONE shared credit-cost formula - the
 * baseline had this pasted three times (here, app/api/bookings/route.ts,
 * and app/studio/dashboard/page.tsx), and only this copy validated
 * anything. This version VALIDATES (throws on a non-positive-integer
 * quantity) instead of clamping - clamping a negative quantity to 1 for
 * the real charge would silently undercharge instead of rejecting the
 * request, reintroducing B-10's bug through the back door. Every real
 * charge (the booking route, the dashboard's historical figures) imports
 * this function; see estimateCreditCostForDisplay below for the one place
 * that legitimately needs different (non-throwing) behaviour.
 */
export function calculateCreditCost(creditCostPerSeat: number, quantity: number): number {
  if (!Number.isInteger(quantity) || quantity <= 0) {
    throw new Error("quantity must be a positive integer");
  }
  return creditCostPerSeat * quantity;
}

/**
 * UI-only: the booking form calls this on every keystroke, including while
 * the input is empty, negative, or mid-edit. Clamping to 1 here is purely
 * cosmetic - it only affects what number is DISPLAYED before submission,
 * never what's actually charged (the real charge always goes through
 * calculateCreditCost, server-side, which rejects bad input outright).
 */
export function estimateCreditCostForDisplay(creditCostPerSeat: number, quantity: number): number {
  const displayQuantity = Number.isInteger(quantity) && quantity > 0 ? quantity : 1;
  return creditCostPerSeat * displayQuantity;
}
