-- Fixed (M6). Closes B-09 (SPEC.md B-09).
--
-- The baseline's `insert into storage.buckets ... on conflict do nothing`
-- would silently no-op if repeated here - the bucket row already exists
-- from migration 2. UPDATE is what actually changes its limits: no SVG (or
-- any type outside this list), and a 2 MiB cap.
update storage.buckets
set file_size_limit = 2097152, -- 2 MiB
    allowed_mime_types = array['image/png', 'image/jpeg', 'image/webp']
where id = 'avatars';
