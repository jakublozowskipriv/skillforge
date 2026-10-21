select
    warehouse_id,
    warehouse_code,
    city as warehouse_city,
    region as warehouse_region
from {{ source('raw', 'warehouses') }}
