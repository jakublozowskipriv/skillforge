select
    complaint_id,
    shipment_id,
    created_at,
    category,
    status as complaint_status,
    compensation_pln
from {{ source('raw', 'complaints') }}
