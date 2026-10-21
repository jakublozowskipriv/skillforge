select
    warehouse_id,
    warehouse_code,
    warehouse_city,
    warehouse_region
from {{ ref('stg_raw__warehouses') }}
