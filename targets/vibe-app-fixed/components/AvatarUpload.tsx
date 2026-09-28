"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

/**
 * B-09 (seeded flaw, SPEC.md B-09): uploads whatever file the user picks,
 * with no client-side OR server-side check on file type or size - the
 * storage policy (see supabase/migrations) accepts any content-type to
 * the caller's own path in the public `avatars` bucket. An uploaded
 * `.svg` with an embedded `<script>` is served back with
 * `Content-Type: image/svg+xml` and no attachment disposition, so it
 * renders (and its script executes) if visited directly - stored XSS.
 */
export default function AvatarUpload({ userId }: { userId: string }) {
  const [status, setStatus] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("Uploading...");
    const supabase = createClient();
    const path = `${userId}/${file.name}`;
    const { error } = await supabase.storage.from("avatars").upload(path, file, { upsert: true });
    if (error) {
      setStatus(`Error: ${error.message}`);
      return;
    }
    const { data } = supabase.storage.from("avatars").getPublicUrl(path);
    setStatus(`Uploaded: ${data.publicUrl}`);
  }

  return (
    <div>
      <label>
        Avatar
        <input type="file" onChange={handleUpload} />
      </label>
      {status && <p>{status}</p>}
    </div>
  );
}
