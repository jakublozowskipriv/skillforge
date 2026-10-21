select
    shipment_id,
    order_id,
    warehouse_id,
    -- WMS free text: ' swift', 'Pako ' → 'SWIFT', 'PAKO'. Fix once here, never downstream.
    upper(trim(carrier_code)) as carrier_code,
    tracking_number,
    created_at,
    parcel_size,
    weight_kg,
    shipping_cost_pln
from {{ source('raw', 'shipments') }}
