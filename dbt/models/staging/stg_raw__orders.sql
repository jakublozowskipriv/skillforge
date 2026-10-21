select
    order_id,
    customer_id,
    warehouse_id,
    ordered_at,
    service_level,
    order_status = 'cancelled' as is_cancelled,
    order_value_pln,
    destination_city,
    destination_region
from {{ source('raw', 'orders') }}
