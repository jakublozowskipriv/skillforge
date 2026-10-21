{#
  Grain: one row per shipment (parcel). Declared in the YAML contract and tested with `unique`.
  Measures are additive per parcel (cost, value) or flags you can average (is_on_time).

  On-time definition (a business decision, documented here and in the YAML):
    promised_at = picked_up_at + sla_hours of the SLA version valid on the pickup date
    is_on_time  = delivered_at <= promised_at   (NULL while not delivered)
  The clock starts at pickup because that is what the carrier controls; first-mile delay
  (label → pickup) is measured separately as first_mile_hours.
#}
with shipments as (
    select * from {{ ref('stg_raw__shipments') }}
),

orders as (
    select * from {{ ref('stg_raw__orders') }}
),

milestones as (
    select * from {{ ref('int_shipment_milestones') }}
),

carriers as (
    select * from {{ ref('dim_carrier') }}
),

sla as (
    select * from {{ ref('dim_carrier_sla') }}
),

complaints as (
    select shipment_id, count(*) as complaints_count
    from {{ ref('stg_raw__complaints') }}
    group by shipment_id
),

joined as (
    select
        s.shipment_id,
        s.order_id,
        c.carrier_id,
        s.warehouse_id,
        sla.carrier_sla_key,
        o.service_level,
        s.parcel_size,
        s.created_at,
        m.picked_up_at,
        m.first_failed_attempt_at,
        m.delivered_at,
        m.returned_at,
        coalesce(m.failed_attempts, 0) as failed_attempts,
        sla.sla_hours,
        m.picked_up_at + sla.sla_hours * interval 1 hour as promised_at,
        s.weight_kg,
        s.shipping_cost_pln,
        coalesce(cp.complaints_count, 0) as complaints_count
    from shipments as s
    inner join orders as o on s.order_id = o.order_id
    inner join carriers as c on s.carrier_code = c.carrier_code
    left join milestones as m on s.shipment_id = m.shipment_id
    left join sla
        on c.carrier_id = sla.carrier_id
        and o.service_level = sla.service_level
        and cast(m.picked_up_at as date) >= sla.valid_from
        and cast(m.picked_up_at as date) < sla.valid_to
    left join complaints as cp on s.shipment_id = cp.shipment_id
)

select
    shipment_id,
    order_id,
    carrier_id,
    warehouse_id,
    carrier_sla_key,
    service_level,
    parcel_size,
    created_at,
    picked_up_at,
    first_failed_attempt_at,
    delivered_at,
    returned_at,
    failed_attempts,
    sla_hours,
    promised_at,
    case
        when delivered_at is not null then 'delivered'
        when returned_at is not null then 'returned'
        when picked_up_at is not null then 'in_transit'
        else 'awaiting_pickup'
    end as shipment_status,
    case when delivered_at is not null then delivered_at <= promised_at end as is_on_time,
    {{ hours_between('created_at', 'picked_up_at') }} as first_mile_hours,
    {{ hours_between('picked_up_at', 'delivered_at') }} as transit_hours,
    weight_kg,
    shipping_cost_pln,
    complaints_count,
    complaints_count > 0 as has_complaint
from joined
