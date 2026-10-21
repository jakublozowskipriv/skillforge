{#
  Deduplication lives in staging because duplicates are a property of the *source* (at-least-once
  delivery from carrier APIs), not of any business logic. Every downstream model can then assume
  one row per (shipment_id, event_type, event_at). We keep the earliest-loaded copy so that
  `loaded_at` reflects when we first knew about the event.
#}
with source as (
    select * from {{ source('raw', 'shipment_events') }}
),

typed as (
    select
        event_id,
        shipment_id,
        event_type,
        strptime(event_at, '%Y-%m-%dT%H:%M:%SZ') as event_at,
        location_city,
        loaded_at
    from source
)

select *
from typed
qualify row_number() over (
    partition by shipment_id, event_type, event_at
    order by loaded_at, event_id
) = 1
