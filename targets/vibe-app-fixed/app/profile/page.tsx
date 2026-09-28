import { getSessionUser } from "@/lib/supabase/server";
import { getMyProfile } from "@/lib/data/profile";
import AvatarUpload from "@/components/AvatarUpload";

export default async function ProfilePage() {
  const user = await getSessionUser();
  if (!user) {
    return <main>Please sign in.</main>;
  }

  const profile = await getMyProfile(user.id);

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
