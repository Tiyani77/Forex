-- Run once in your Supabase project's SQL Editor.
-- A dedicated research table; no client-side read/write policies.
create table if not exists public.forex_predictions (
    id uuid primary key default gen_random_uuid(),
    recorded_at timestamptz not null default now(),
    instrument text not null,
    ticker text not null,
    timeframe text not null check (timeframe in ('5m','15m','1h','4h','1d')),
    signal text not null check (signal in ('BUY','SELL','WAIT')),
    model_version text not null,
    signal_bar_at timestamptz not null,
    reference_close double precision not null check (reference_close > 0),
    horizon_bars integer not null check (horizon_bars between 1 and 100),
    status text not null default 'pending' check (status in ('pending','evaluated','unavailable')),
    evaluated_at timestamptz,
    outcome_bar_at timestamptz,
    outcome_close double precision,
    directional_return_pct double precision,
    correct boolean,
    constraint evaluated_has_outcome check (
        status <> 'evaluated' or (evaluated_at is not null and outcome_bar_at is not null and outcome_close is not null)
    )
);
create index if not exists forex_predictions_status_idx on public.forex_predictions(status, recorded_at);
alter table public.forex_predictions enable row level security;
-- No RLS policies: browser/anon clients cannot read or write predictions.
-- The Streamlit backend uses the server-side service-role key.
