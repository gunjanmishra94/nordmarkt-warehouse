-- Fails (returns rows) if a delivery is recorded at or before its shipment.
-- Guards specifically against the generator/model regressing to a single
-- shipment event per order, which made hours_shipped_to_delivered always
-- exactly zero for every delivered order — see DECISIONS.md.
select
    order_id,
    shipped_at,
    delivered_at
from {{ ref('fct_order_fulfilment') }}
where
    delivered_at is not null
    and delivered_at <= shipped_at
