"use client";

/**
 * B-11 (seeded flaw, SPEC.md B-11): this client component only ever
 * RENDERS `member.full_name` - but the parent server component
 * (app/studio/members/page.tsx) passes the entire profile row as props,
 * including email and phone. Next.js serialises the full prop object into
 * the page's payload, so that PII ships to every visitor's browser
 * regardless of what this component chooses to display.
 */
export default function MemberNameList({ members }: { members: any[] }) {
  return (
    <ul>
      {members.map((m) => (
        <li key={m.id}>{m.full_name}</li>
      ))}
    </ul>
  );
}
