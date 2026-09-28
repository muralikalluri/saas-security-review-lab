import { describe, expect, it } from "vitest";
import { calculateCreditCost, estimateCreditCostForDisplay } from "./pricing";

/**
 * B-12 (fixed, SPEC.md B-12): "no tests" was part of this finding. These
 * cover exactly the shape of bug B-10 came from - a negative/zero/non-
 * integer quantity must be REJECTED by the real charge formula, not
 * clamped to something plausible-looking.
 */
describe("calculateCreditCost", () => {
  it("multiplies cost per seat by a valid positive-integer quantity", () => {
    expect(calculateCreditCost(3, 2)).toBe(6);
    expect(calculateCreditCost(1, 1)).toBe(1);
  });

  it("throws on a negative quantity", () => {
    expect(() => calculateCreditCost(1, -5)).toThrow(/positive integer/);
  });

  it("throws on a zero quantity", () => {
    expect(() => calculateCreditCost(1, 0)).toThrow(/positive integer/);
  });

  it("throws on a non-integer quantity", () => {
    expect(() => calculateCreditCost(1, 1.5)).toThrow(/positive integer/);
  });

  it("throws on NaN/Infinity", () => {
    expect(() => calculateCreditCost(1, NaN)).toThrow(/positive integer/);
    expect(() => calculateCreditCost(1, Infinity)).toThrow(/positive integer/);
  });
});

describe("estimateCreditCostForDisplay", () => {
  it("matches calculateCreditCost for valid input", () => {
    expect(estimateCreditCostForDisplay(3, 2)).toBe(6);
  });

  it("clamps a negative/zero/non-integer quantity to 1 - display only, never throws", () => {
    expect(estimateCreditCostForDisplay(3, -5)).toBe(3);
    expect(estimateCreditCostForDisplay(3, 0)).toBe(3);
    expect(estimateCreditCostForDisplay(3, 1.5)).toBe(3);
  });
});
