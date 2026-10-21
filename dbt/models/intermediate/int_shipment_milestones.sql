{#
  Pivot: event stream (long) → one row per shipment with a timestamp per milestone (wide).
  min() because a milestone that happened twice (e.g. two failed attempts) should report
  the first occurrence; the count of failed attempts is kept separately.
#}
select
    shipment_id,
    min(event_at) filter (where event_type = 'label_created') as label_created_at,
    min(event_at) filter (where event_type = 'picked_up') as picked_up_at,
    min(event_at) filter (where event_type = 'in_transit') as in_transit_at,
    min(event_at) filter (where event_type = 'out_for_delivery') as out_for_delivery_at,
    min(event_at) filter (where event_type = 'delivery_failed') as first_failed_attempt_at,
    min(event_at) filter (where event_type = 'delivered') as delivered_at,
    min(event_at) filter (where event_type = 'returned') as returned_at,
    count(*) filter (where event_type = 'delivery_failed') as failed_attempts,
    max(loaded_at) as last_loaded_at
from {{ ref('stg_raw__shipment_events') }}
group by shipment_id
