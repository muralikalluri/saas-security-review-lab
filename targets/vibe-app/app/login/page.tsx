"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("maya.member@studiobook-fictional.example");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      setError(error.message);
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <main>
      <h1>StudioBook (fictional) - sign in</h1>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.5rem", maxWidth: 320 }}>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button type="submit">Sign in</button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </form>
      <p style={{ fontSize: "0.85rem", color: "#555" }}>
        Demo users (password <code>LabPassword-Only-1</code> for all): maya.member, liam.member, noah.admin
        @studiobook-fictional.example
      </p>
    </main>
  );
}
