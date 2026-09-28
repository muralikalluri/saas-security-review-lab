import { createClient, getSessionUser } from "@/lib/supabase/server";
import AvatarUpload from "@/components/AvatarUpload";

export default async function ProfilePage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const supabase = createClient();
  const { data: profile } = await supabase.from("profiles").select("*").eq("id", user.id).single();

  return (
    <main>
      <h1>My profile</h1>
      <p>Name: {profile?.full_name}</p>
      <p>Email: {profile?.email}</p>
      <p>Credit balance: {profile?.credit_balance}</p>
      <AvatarUpload userId={user.id} />
    </main>
  );
}
