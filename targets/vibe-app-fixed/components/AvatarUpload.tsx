"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

const ALLOWED_TYPES: Record<string, string> = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/webp": "webp",
};
const MAX_BYTES = 2 * 1024 * 1024; // 2 MiB - matches the bucket's own file_size_limit

/**
 * B-09 (fixed, SPEC.md B-09): the storage bucket itself now enforces
 * file_size_limit and allowed_mime_types (see the migration) - that's the
 * real barrier, since Supabase Storage checks both server-side regardless
 * of what this component does. The checks here are client-side UX (fail
 * fast instead of attempting a doomed upload) plus using a fixed filename
 * with an extension derived from the VALIDATED type, instead of the raw,
 * attacker-controlled `file.name` - the stored path can never end in
 * `.svg` or anything else outside the allow-list.
 */
export default function AvatarUpload({ userId }: { userId: string }) {
  const [status, setStatus] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = ALLOWED_TYPES[file.type];
    if (!ext) {
      setStatus(`Rejected: "${file.type || "unknown type"}" is not an allowed image type (png/jpeg/webp only).`);
      return;
    }
    if (file.size > MAX_BYTES) {
      setStatus(`Rejected: file is larger than ${MAX_BYTES / 1024 / 1024} MiB.`);
      return;
    }

    setStatus("Uploading...");
    const supabase = createClient();
    const path = `${userId}/avatar.${ext}`;
    const { error } = await supabase.storage.from("avatars").upload(path, file, { upsert: true, contentType: file.type });
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
        <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleUpload} />
      </label>
      {status && <p>{status}</p>}
    </div>
  );
}
