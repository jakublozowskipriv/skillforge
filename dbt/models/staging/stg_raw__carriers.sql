select
    carrier_id,
    upper(trim(carrier_code)) as carrier_code,
    carrier_name,
    service_type
from {{ source('raw', 'carriers') }}
