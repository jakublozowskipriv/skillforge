{#
  SCD type 2 dimension: one row per *version* of a carrier's SLA.
  - valid_to is exclusive and never NULL (open-ended rows get 9999-12-31) so that a point-in-time
    join is a simple `ts >= valid_from and ts < valid_to` with no NULL handling.
  - The surrogate key identifies the version, not the carrier — facts can reference the exact
    SLA that applied when the parcel was picked up.
#}
select
    {{ surrogate_key(['carrier_id', 'service_level', 'valid_from']) }} as carrier_sla_key,
    carrier_id,
    service_level,
    sla_hours,
    valid_from,
    coalesce(valid_to, date '9999-12-31') as valid_to,
    valid_to is null as is_current
from {{ ref('stg_raw__carrier_sla_history') }}
