select
    pickup_id,
    warehouse_id,
    carrier_id,
    window_start_at,
    window_end_at,
    arrived_at,
    departed_at,
    parcels_collected,
    arrived_at is null as is_no_show
from {{ source('raw', 'courier_pickups') }}
