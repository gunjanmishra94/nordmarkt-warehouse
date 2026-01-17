-- Fails (returns rows) if a single order's allocated discount across its
-- lines doesn't add back up to the discount actually applied on that order.
-- Tolerance covers per-line cent rounding on orders with a handful of lines.
select
    order_id,
    sum(allocated_discount_eur) as allocated_total,
    max(order_discount_amount_eur) as order_total
from {{ ref('fct_order_lines') }}
group by order_id
having abs(sum(allocated_discount_eur) - max(order_discount_amount_eur)) > 0.03
