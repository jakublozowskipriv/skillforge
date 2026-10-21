-- Singular test: a parcel cannot be delivered before the courier picked it up.
-- Returns failing rows (0 rows = pass). TODO(learn) #2 generalizes this into a generic test.
select shipment_id, picked_up_at, delivered_at
from {{ ref('fct_shipments') }}
where delivered_at < picked_up_at
