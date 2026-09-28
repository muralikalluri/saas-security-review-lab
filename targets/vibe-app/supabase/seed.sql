-- Deliberately insecure for demonstration. Do not deploy.
-- Fictional demo data for StudioBook. All names/emails are fictional.
-- Password for every seeded user: LabPassword-Only-1 (a local Supabase
-- dev credential, not a leaked secret).

create extension if not exists pgcrypto with schema extensions;

-- Users (via auth.users + auth.identities directly - this is a local-only
-- seed script, not something a real app would ever do against a live
-- Supabase project).
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at, confirmation_token, email_change,
    email_change_token_new, recovery_token
) values
    ('00000000-0000-0000-0000-000000000000', '11111111-1111-1111-1111-111111111111',
     'authenticated', 'authenticated', 'maya.member@studiobook-fictional.example',
     crypt('LabPassword-Only-1', gen_salt('bf')), now(),
     '{"provider":"email","providers":["email"]}', '{}', now(), now(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', '22222222-2222-2222-2222-222222222222',
     'authenticated', 'authenticated', 'liam.member@studiobook-fictional.example',
     crypt('LabPassword-Only-1', gen_salt('bf')), now(),
     '{"provider":"email","providers":["email"]}', '{}', now(), now(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', '33333333-3333-3333-3333-333333333333',
     'authenticated', 'authenticated', 'noah.admin@studiobook-fictional.example',
     crypt('LabPassword-Only-1', gen_salt('bf')), now(),
     '{"provider":"email","providers":["email"]}', '{}', now(), now(), '', '', '', '');

insert into auth.identities (
    id, user_id, provider_id, identity_data, provider, last_sign_in_at, created_at, updated_at
) values
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111',
     jsonb_build_object('sub', '11111111-1111-1111-1111-111111111111', 'email', 'maya.member@studiobook-fictional.example'),
     'email', now(), now(), now()),
    (gen_random_uuid(), '22222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222',
     jsonb_build_object('sub', '22222222-2222-2222-2222-222222222222', 'email', 'liam.member@studiobook-fictional.example'),
     'email', now(), now(), now()),
    (gen_random_uuid(), '33333333-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333',
     jsonb_build_object('sub', '33333333-3333-3333-3333-333333333333', 'email', 'noah.admin@studiobook-fictional.example'),
     'email', now(), now(), now());

insert into public.profiles (id, full_name, email, phone, role, credit_balance) values
    ('11111111-1111-1111-1111-111111111111', 'Maya Fictional', 'maya.member@studiobook-fictional.example', '+1-555-0301', 'member', 5),
    ('22222222-2222-2222-2222-222222222222', 'Liam Fictional', 'liam.member@studiobook-fictional.example', '+1-555-0302', 'member', 2),
    ('33333333-3333-3333-3333-333333333333', 'Noah Fictional', 'noah.admin@studiobook-fictional.example', '+1-555-0303', 'admin', 0);

insert into public.classes (id, title, instructor, studio_name, capacity, price_cents, credit_cost, starts_at) values
    ('aaaaaaaa-0000-0000-0000-000000000001', 'Sunrise Vinyasa Flow', 'Priya Fictional', 'StudioBook Downtown (fictional)', 12, 2500, 1, now() + interval '1 day'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 'Contemporary Dance Basics', 'Jordan Fictional', 'StudioBook Riverside (fictional)', 8, 3000, 1, now() + interval '2 days');

-- A pre-existing booking for maya - used by exploits/B-05 (liam cancels it).
insert into public.bookings (id, user_id, class_id, quantity, status) values
    ('bbbbbbbb-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-0000-0000-0000-000000000001', 1, 'confirmed');
