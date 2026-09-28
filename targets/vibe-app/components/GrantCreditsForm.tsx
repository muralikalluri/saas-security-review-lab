"use client";

import { useState } from "react";

export default function GrantCreditsForm() {
  const [targetUserId, setTargetUserId] = useState("");
  const [amount, setAmount] = useState(1);
  const [result, setResult] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/admin/grant-credits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ targetUserId, amount }),
    });
    const body = await res.json();
    setResult(res.ok ? `New balance: ${body.profile.credit_balance}` : `Error: ${body.error}`);
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.5rem", maxWidth: 320 }}>
      <label>
        User id
        <input value={targetUserId} onChange={(e) => setTargetUserId(e.target.value)} required />
      </label>
      <label>
        Amount
        <input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} required />
      </label>
      <button type="submit">Grant</button>
      {result && <p>{result}</p>}
    </form>
  );
}
