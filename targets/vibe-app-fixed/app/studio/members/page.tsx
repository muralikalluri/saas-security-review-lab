import { createClient, getSessionUser } from "@/lib/supabase/server";
import MemberNameList from "@/components/MemberNameList";

export default async function StudioMembersPage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const supabase = createClient();
  // B-11 (seeded flaw, SPEC.md B-11): selects every column (including
  // email/phone) for every OTHER member, not just the `full_name` the
  // page actually displays - see MemberNameList.tsx.
  const { data: members } = await supabase.from("profiles").select("*").neq("id", user.id);

  return (
    <main>
      <h1>Studio members</h1>
      <MemberNameList members={members ?? []} />
    </main>
  );
}
