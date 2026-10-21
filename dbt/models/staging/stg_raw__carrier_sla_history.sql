select
    carrier_id,
    service_level,
    sla_hours,
    valid_from,
    valid_to
from {{ source('raw', 'carrier_sla_history') }}
