"use client";

/**
 * B-11 (fixed, SPEC.md B-11): the parent server component
 * (app/studio/members/page.tsx) now selects only {id, full_name} - there is
 * no PII in `members` for this component to receive in the first place,
 * regardless of what it renders.
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
