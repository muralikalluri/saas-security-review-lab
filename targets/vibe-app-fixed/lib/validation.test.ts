import { describe, expect, it } from "vitest";
import { isPositiveIntegerWithinBound } from "./validation";

describe("isPositiveIntegerWithinBound", () => {
  it("accepts a valid positive integer within bound", () => {
    expect(isPositiveIntegerWithinBound(1, 20)).toBe(true);
    expect(isPositiveIntegerWithinBound(20, 20)).toBe(true);
  });

  it("rejects negative, zero, and above-bound values", () => {
    expect(isPositiveIntegerWithinBound(-5, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(0, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(21, 20)).toBe(false);
  });

  it("rejects non-integers, NaN, Infinity, and non-numbers (the B-10 shapes)", () => {
    expect(isPositiveIntegerWithinBound(1.5, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(NaN, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(Infinity, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound("5", 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(null, 20)).toBe(false);
    expect(isPositiveIntegerWithinBound(undefined, 20)).toBe(false);
  });
});
