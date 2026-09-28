import type { ReactNode } from "react";

export const metadata = {
  title: "StudioBook (fictional) - deliberately insecure demo",
  description: "Deliberately insecure for demonstration. Do not deploy.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: "1.5rem", maxWidth: 720, marginInline: "auto" }}>
        <p style={{ background: "#fee2e2", color: "#991b1b", padding: "0.5rem 1rem", borderRadius: 4, fontSize: "0.85rem" }}>
          Deliberately insecure for demonstration. Do not deploy. Run locally only.
        </p>
        {children}
      </body>
    </html>
  );
}
