// Deliberately insecure for demonstration. Do not deploy.
// semgrep --test fixtures for b05-missing-ownership-check.

async function badUpdateNoOwnershipCheck(supabase: any, params: { id: string }) {
  // ruleid: b05-missing-ownership-check
  const { data } = await supabase.from("bookings").update({ status: "cancelled" }).eq("id", params.id).select().single();
  return data;
}

async function badDeleteNoOwnershipCheck(supabase: any, id: string) {
  // ruleid: b05-missing-ownership-check
  await supabase.from("notes").delete().eq("id", id);
}

async function okUpdateWithOwnershipCheckAfter(supabase: any, params: { id: string }, userId: string) {
  // ok: b05-missing-ownership-check
  const { data } = await supabase.from("bookings").update({ status: "cancelled" }).eq("id", params.id).eq("user_id", userId).select().single();
  return data;
}

async function okDeleteWithOwnershipCheckAfter(supabase: any, id: string, userId: string) {
  // ok: b05-missing-ownership-check
  await supabase.from("notes").delete().eq("id", id).eq("user_id", userId);
}

async function okUpdateWithOwnershipCheckFirst(supabase: any, params: { id: string }, userId: string) {
  // ok: b05-missing-ownership-check
  const { data } = await supabase.from("bookings").update({ status: "cancelled" }).eq("user_id", userId).eq("id", params.id).select().single();
  return data;
}

async function okUpdateWithMatchOwnershipCheck(supabase: any, params: { id: string }, userId: string) {
  // ok: b05-missing-ownership-check
  const { data } = await supabase.from("bookings").update({ status: "cancelled" }).eq("id", params.id).match({ user_id: userId }).select().single();
  return data;
}

async function okUpdateWithNoIdFilterAtAll(supabase: any, payload: any) {
  // ok: b05-missing-ownership-check
  await supabase.from("settings").update(payload);
}
