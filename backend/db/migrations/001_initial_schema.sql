create table style_profiles (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  board_ids text[] not null default '{}',
  anchor_pin_urls text[] not null default '{}',
  style_context_path text
);

create table style_features (
  id uuid primary key default gen_random_uuid(),
  style_profile_id uuid not null references style_profiles(id) on delete cascade,
  label text not null,
  confidence float not null,
  examples text[] not null default '{}'
);

create table user_preferences (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  sizes text[] not null default '{}',
  price_min float,
  price_max float,
  brand_allowlist text[] not null default '{}',
  brand_blocklist text[] not null default '{}'
);

create table listings (
  id text primary key,
  style_profile_id uuid references style_profiles(id) on delete set null,
  title text not null,
  price float not null,
  brand text,
  size text,
  image_urls text[] not null default '{}',
  vinted_url text not null,
  score float,
  reasoning text,
  feedback text check (feedback in ('liked', 'disliked'))
);
