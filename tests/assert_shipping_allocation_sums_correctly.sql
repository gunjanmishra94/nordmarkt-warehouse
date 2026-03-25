-- Fails (returns rows) if a single order's allocated shipping across its
-- lines doesn't add back up to the shipping actually charged on that order.
-- Tolerance covers per-line cent rounding on orders with a handful of lines.
select
    order_id,
    sum(allocated_shipping_eur) as allocated_total,
    max(order_shipping_amount_eur) as order_total
from {{ ref('fct_order_lines') }}
group by order_id
having abs(sum(allocated_shipping_eur) - max(order_shipping_amount_eur)) > 0.03
