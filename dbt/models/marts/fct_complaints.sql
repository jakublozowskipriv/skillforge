{# Grain: one row per complaint. Carrier and warehouse come from the shipment (conformed dims). #}
select
    c.complaint_id,
    c.shipment_id,
    s.carrier_id,
    s.warehouse_id,
    c.created_at,
    cast(c.created_at as date) as created_date,
    c.category,
    c.complaint_status,
    c.compensation_pln,
    {{ hours_between('s.delivered_at', 'c.created_at') }} as hours_since_delivery
from {{ ref('stg_raw__complaints') }} as c
inner join {{ ref('fct_shipments') }} as s on c.shipment_id = s.shipment_id
