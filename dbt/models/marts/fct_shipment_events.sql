{#
  Incremental event fact. Why incremental + lookback:
  - events are append-mostly and large, so we only process what is new since the last run;
  - but carriers send some events days late, so "new" is judged by `loaded_at`, and we re-read a
    window of `event_lookback_days` before the current max to catch stragglers;
  - `unique_key` makes the re-read idempotent: rows already present are updated, not duplicated.
  `skillforge data build` runs with --full-refresh because it regenerates raw from scratch.
#}
{{
    config(
        materialized='incremental',
        unique_key='event_key',
        incremental_strategy='delete+insert',
    )
}}

select
    {{ surrogate_key(['shipment_id', 'event_type', 'event_at']) }} as event_key,
    event_id,
    shipment_id,
    event_type,
    event_at,
    cast(event_at as date) as event_date,
    location_city,
    loaded_at
from {{ ref('stg_raw__shipment_events') }}

{% if is_incremental() %}
where loaded_at > (
    select max(loaded_at) - interval {{ var('event_lookback_days') }} day from {{ this }}
)
{% endif %}
