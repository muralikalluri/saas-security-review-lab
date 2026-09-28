/**
 * B-10/B-12 (fixed, SPEC.md B-10/B-12): a small, testable predicate instead
 * of an inline condition buried in the route handler - the exact
 * NaN/Infinity/float/string/zero/negative shapes that used to slip through
 * are what lib/validation.test.ts checks directly, without needing a live
 * DB or an HTTP request.
 */
export function isPositiveIntegerWithinBound(value: unknown, max: number): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0 && value <= max;
}
