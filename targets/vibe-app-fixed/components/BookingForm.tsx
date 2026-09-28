"use client";

import { useState } from "react";
import { estimateCreditCostForDisplay } from "@/lib/pricing";

export default function BookingForm({ classId, creditCostPerSeat }: { classId: string; creditCostPerSeat: number }) {
  const [quantity, setQuantity] = useState(1);
  const [result, setResult] = useState<string | null>(null);

  // Display-only estimate (see lib/pricing.ts) - the server independently
  // validates and charges via calculateCreditCost; this is just what's
  // shown before submitting.
  const estimatedCost = estimateCreditCostForDisplay(creditCostPerSeat, quantity);

  async function handleBook() {
    setResult(null);
    const res = await fetch("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ classId, quantity }),
    });
    const body = await res.json();
    setResult(res.ok ? `Booked. New credit balance: ${body.creditBalance}` : `Error: ${body.error}`);
  }

  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 6, padding: "0.75rem", marginTop: "1rem" }}>
      <label>
        Seats
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          style={{ marginLeft: "0.5rem", width: "5rem" }}
        />
      </label>
      <p>Estimated cost: {estimatedCost} credit(s)</p>
      <button onClick={handleBook}>Book</button>
      {result && <p>{result}</p>}
    </div>
  );
}
