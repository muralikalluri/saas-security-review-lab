-- Deliberately insecure for demonstration. Do not deploy.
-- StudioBook (fictional) baseline schema. All data is fictional.

create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text not null,
    email text not null,
    phone text,
    role text not null default 'member' check (role in ('member', 'admin')),
    credit_balance integer not null default 0,
    avatar_url text,
    created_at timestamptz not null default now()
);

create table public.classes (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    instructor text not null,
    studio_name text not null,
    capacity integer not null,
    price_cents integer not null,
    credit_cost integer not null,
    starts_at timestamptz not null
);

create table public.bookings (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    class_id uuid not null references public.classes(id) on delete cascade,
    quantity integer not null default 1,
    status text not null default 'confirmed' check (status in ('confirmed', 'cancelled')),
    created_at timestamptz not null default now()
);

create index idx_bookings_user on public.bookings(user_id);
create index idx_bookings_class on public.bookings(class_id);
