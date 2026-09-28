-- Fixed (M6 follow-up). Closes B-09 (SPEC.md B-09) - functional regression
-- found by a milestone review, not a security gap: migration 2 only granted
-- INSERT and SELECT on storage.objects for the avatars bucket, never UPDATE.
-- components/AvatarUpload.tsx uploads to a fixed per-user path with
-- `upsert: true`, so re-uploading (replacing an existing avatar) resolves to
-- an UPDATE, which RLS was silently denying - a user could set an avatar
-- once and never change it. Owner-scoped, same path rule as the INSERT
-- policy from migration 2.
create policy "avatars_update_own_path_b09" on storage.objects
    for update to authenticated
    using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text)
    with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);
