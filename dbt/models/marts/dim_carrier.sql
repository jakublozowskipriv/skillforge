select
    carrier_id,
    carrier_code,
    carrier_name,
    service_type
from {{ ref('stg_raw__carriers') }}
