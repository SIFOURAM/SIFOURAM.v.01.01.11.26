begin;

create extension if not exists pgcrypto;

create type public.app_role as enum ('owner', 'admin', 'barteam', 'rider');

create table public.users (
  id uuid primary key default gen_random_uuid(),
  username text not null unique,
  email text,
  whatsapp text,
  name text not null,
  role public.app_role not null default 'rider',
  active boolean not null default true,
  password_hash text not null,
  pin_hash text not null,
  photo text,
  banks jsonb not null default '[]'::jsonb,
  settings jsonb not null default '{}'::jsonb,
  consent jsonb,
  joined_at date,
  placement text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.materials (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  unit text not null,
  pack_qty numeric not null,
  pack_price numeric not null,
  pack_label text not null,
  category text not null,
  stock numeric not null default 0,
  min_stock numeric not null default 0,
  created_at timestamptz not null default now()
);

create table public.menus (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  price numeric not null,
  max_stock integer not null,
  stock integer not null default 0,
  recipe jsonb not null default '[]'::jsonb,
  photo text,
  active boolean not null default true,
  display_order integer not null default 0,
  created_at timestamptz not null default now()
);

create table public.attendance (
  id uuid primary key default gen_random_uuid(),
  rider_id uuid not null references public.users(id),
  date date not null,
  checkin_at timestamptz,
  checkout_at timestamptz,
  checkin_photo text,
  checkout_photo text,
  created_at timestamptz not null default now(),
  unique (rider_id, date)
);

create table public.rider_stock (
  id uuid primary key default gen_random_uuid(),
  rider_id uuid not null references public.users(id),
  date date not null,
  items jsonb not null default '{}'::jsonb,
  photo text,
  created_at timestamptz not null default now(),
  unique (rider_id, date)
);

create table public.sales (
  id uuid primary key default gen_random_uuid(),
  client_id uuid unique,
  receipt_no text not null unique,
  rider_id uuid not null references public.users(id),
  date date not null,
  sale_time time not null,
  items jsonb not null,
  total numeric not null,
  cups integer not null,
  payment_method text not null,
  customer_name text,
  customer_phone text,
  created_at timestamptz not null default now()
);

create table public.deposits (
  id uuid primary key default gen_random_uuid(),
  rider_id uuid not null references public.users(id),
  date date not null,
  rows jsonb not null,
  total_cash numeric not null default 0,
  total_qris numeric not null default 0,
  total_cups integer not null default 0,
  net_cash numeric not null default 0,
  created_at timestamptz not null default now(),
  unique (rider_id, date)
);

create table public.inventory_transactions (
  id uuid primary key default gen_random_uuid(),
  material_id uuid not null references public.materials(id),
  transaction_type text not null,
  qty numeric not null,
  cost numeric not null default 0,
  date date not null,
  note text,
  created_by uuid references public.users(id),
  created_at timestamptz not null default now()
);

create table public.coach_chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id),
  provider text not null,
  message text not null,
  reply text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.gps_locations (
  rider_id uuid primary key references public.users(id),
  lat numeric not null,
  lng numeric not null,
  updated_at timestamptz not null default now()
);

create index sales_rider_date_idx on public.sales (rider_id, date);
create index sales_date_idx on public.sales (date);
create index attendance_rider_date_idx on public.attendance (rider_id, date);
create index deposits_rider_date_idx on public.deposits (rider_id, date);
create index inventory_transactions_date_idx on public.inventory_transactions (date);
create index coach_chats_user_created_idx on public.coach_chats (user_id, created_at desc);

alter table public.users enable row level security;
alter table public.materials enable row level security;
alter table public.menus enable row level security;
alter table public.attendance enable row level security;
alter table public.rider_stock enable row level security;
alter table public.sales enable row level security;
alter table public.deposits enable row level security;
alter table public.inventory_transactions enable row level security;
alter table public.coach_chats enable row level security;
alter table public.gps_locations enable row level security;

create function public.current_app_role()
returns text
language sql stable
as $$ select current_setting('app.role', true) $$;

create function public.current_app_user_id()
returns uuid
language sql stable
as $$ select nullif(current_setting('app.user_id', true), '')::uuid $$;

create policy users_owner_access on public.users
  for all using (public.current_app_role() = 'owner')
  with check (public.current_app_role() = 'owner');

create policy rider_own_user on public.users
  for select using (id = public.current_app_user_id());

create policy attendance_owner_staff on public.attendance
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy attendance_rider_own on public.attendance
  for all using (rider_id = public.current_app_user_id())
  with check (rider_id = public.current_app_user_id());

create policy sales_owner_staff on public.sales
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy sales_rider_own on public.sales
  for select using (rider_id = public.current_app_user_id());

create policy rider_stock_owner_staff on public.rider_stock
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy rider_stock_rider_own on public.rider_stock
  for select using (rider_id = public.current_app_user_id());

create policy deposits_owner_staff on public.deposits
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy deposits_rider_own on public.deposits
  for select using (rider_id = public.current_app_user_id());

create policy materials_staff on public.materials
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy menus_every_authenticated_role on public.menus
  for select using (public.current_app_role() in ('owner', 'admin', 'barteam', 'rider'));

create policy inventory_transactions_staff on public.inventory_transactions
  for all using (public.current_app_role() in ('owner', 'admin', 'barteam'))
  with check (public.current_app_role() in ('owner', 'admin', 'barteam'));

create policy chats_own on public.coach_chats
  for all using (user_id = public.current_app_user_id())
  with check (user_id = public.current_app_user_id());

create policy gps_owner_access on public.gps_locations
  for select using (public.current_app_role() = 'owner');

create policy gps_rider_own on public.gps_locations
  for all using (rider_id = public.current_app_user_id())
  with check (rider_id = public.current_app_user_id());

commit;