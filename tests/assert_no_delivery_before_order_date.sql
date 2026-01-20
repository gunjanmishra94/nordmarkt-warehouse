-- Fails (returns rows) if an order was delivered before it was placed.
select
    order_id,
    placed_at,
    delivered_at
from {{ ref('fct_order_fulfilment') }}
where
    delivered_at is not null
    and delivered_at < placed_at
